"""
Ascendra — AI Service.

Prompt building, provider routing, validation, and audit logging.
AI never writes to the DB directly — it returns suggestions.
"""

import hashlib
import json
import logging
from collections import OrderedDict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import AIGeneration
from app.providers.ai.base import AIProvider, AIResponse
from app.providers.ai.gemini import gemini_provider
from app.providers.ai.groq import groq_provider
from app.resumes.service import resume_service
from app.jobs.service import job_service
from app.applications.service import application_service

logger = logging.getLogger("ascendra.ai")

RESUME_PROMPT_VERSION = "v1.0"
EMAIL_PROMPT_VERSION = "v1.0"

# ── Bounded prompt cache (LRU-style) ─────────────────────────
_MAX_CACHE_SIZE = 256


class _LRUCache(OrderedDict):
    """Simple LRU cache with a max size — prevents unbounded memory growth."""

    def __init__(self, maxsize: int = _MAX_CACHE_SIZE):
        super().__init__()
        self._maxsize = maxsize

    def get_cached(self, key: str) -> dict | None:
        if key in self:
            self.move_to_end(key)
            return self[key]
        return None

    def put(self, key: str, value: dict) -> None:
        self[key] = value
        self.move_to_end(key)
        if len(self) > self._maxsize:
            self.popitem(last=False)


_prompt_cache = _LRUCache()


def _clean_llm_json(raw: str) -> str:
    """Strip markdown codeblock wrappers (```json ... ```) from LLM responses."""
    text = raw.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
        else:
            text = text[3:]  # Just strip the opening ```
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def _flatten_skills(skills_data) -> list[str]:
    """Flatten skills from various AI output formats into a simple string list."""
    if not skills_data:
        return []
    if isinstance(skills_data, str):
        return [s.strip() for s in skills_data.split(",") if s.strip()]
    if isinstance(skills_data, list):
        result = []
        for item in skills_data:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                # Handle {"name": "Python", ...} or {"skill": "Python", ...}
                name = item.get("name") or item.get("skill") or item.get("title") or str(item)
                result.append(str(name))
        return result
    return []


class AIService:
    """
    Orchestrates AI generation for resumes and emails.

    Encapsulates provider fallback logic, audit logging, and prompt caching
    so that generate_resume() and generate_email() stay thin orchestration methods.
    """

    # ── Provider Fallback ─────────────────────────────────────

    @staticmethod
    async def _call_with_fallback(
        primary: AIProvider,
        fallback: AIProvider,
        prompt: str,
        system_prompt: str,
        temperature: float,
        fallback_response_factory: callable,
    ) -> AIResponse:
        """
        Try the primary AI provider; if it fails, try the fallback.
        If both fail, call fallback_response_factory() to produce a local template.
        """
        try:
            return await primary.generate_structured(
                prompt=prompt, system_prompt=system_prompt, temperature=temperature
            )
        except Exception as e:
            logger.warning(
                f"Primary AI provider ({primary.provider_name}) failed: {e}. "
                f"Falling back to {fallback.provider_name}..."
            )
            try:
                return await fallback.generate_structured(
                    prompt=prompt, system_prompt=system_prompt, temperature=temperature
                )
            except Exception as e2:
                logger.error(
                    f"All AI providers failed ({e2}). Using local template fallback."
                )
                return fallback_response_factory()

    # ── Audit Logging ─────────────────────────────────────────

    @staticmethod
    async def _log_generation(
        db: AsyncSession,
        user_id: str,
        generation_type: str,
        prompt_version: str,
        response: AIResponse,
        prompt: str,
        input_context: dict,
        temperature: float,
    ) -> AIGeneration:
        """Create an immutable AIGeneration audit record."""
        generation = AIGeneration(
            user_id=user_id,
            generation_type=generation_type,
            prompt_version=prompt_version,
            model_used=response.model,
            prompt_text=prompt[:10000],
            response_text=response.content[:10000],
            input_context=input_context,
            temperature=temperature,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
        )
        db.add(generation)
        await db.flush()
        return generation

    # ── Resume Summary Extraction ─────────────────────────────

    @staticmethod
    def _extract_resume_summary(structured_data: dict | None) -> str:
        """
        Build a human-readable summary string from structured resume data.

        Used by email generation to provide context about the candidate.
        """
        if not structured_data:
            return ""

        parts: list[str] = []
        if structured_data.get("summary"):
            parts.append(f"Summary: {structured_data['summary']}")
        if structured_data.get("skills"):
            parts.append(f"Skills: {structured_data['skills']}")
        if structured_data.get("experience"):
            parts.append(f"Experience: {structured_data['experience']}")
        return "\n".join(parts)

    # ── Resume Generation ─────────────────────────────────────

    async def generate_resume_flow(
        self,
        db: AsyncSession,
        user_id: str,
        resume_id: str,
        job_id: str | None,
        label: str,
        tailoring_style: str = "ats_optimized",
        focus_keywords: list[str] | None = None,
        custom_instructions: str | None = None,
    ) -> dict:
        """Full orchestration: fetch data → synthesize → generate → persist version."""
        from app.resumes.models import Resume

        # Fetch requested resume as primary
        primary_resume = await resume_service.get_resume(
            db=db, resume_id=resume_id, user_id=user_id
        )

        # Synthesize multi-resume knowledge pool across all user's active resumes
        res_query = await db.execute(
            select(Resume).where(
                Resume.user_id == user_id
            )
        )
        all_resumes = res_query.scalars().all()

        combined_structured = dict(primary_resume.structured_data or {})
        combined_skills: set[str] = set()
        raw_skills = combined_structured.get("skills")
        if isinstance(raw_skills, list):
            combined_skills.update(raw_skills)

        for other_res in all_resumes:
            if other_res.id == primary_resume.id or not other_res.structured_data:
                continue
            sdata = other_res.structured_data
            other_skills = sdata.get("skills")
            if isinstance(other_skills, list):
                combined_skills.update(other_skills)
            elif isinstance(other_skills, str):
                combined_skills.add(other_skills)
            other_exp = sdata.get("experience")
            if isinstance(other_exp, list):
                existing_exp = combined_structured.get("experience", [])
                if isinstance(existing_exp, list):
                    combined_structured["experience"] = existing_exp + other_exp

        if combined_skills:
            combined_structured["skills"] = list(combined_skills)

        # Fetch job context if targeting a specific role
        job_description = job_title = company_name = None
        if job_id:
            job = await job_service.get_job(db=db, job_id=job_id, user_id=user_id)
            job_description = job.description
            job_title = job.title
            company_name = job.company.name if job.company else None

        result = await self._generate_resume(
            db=db,
            user_id=user_id,
            structured_resume=combined_structured,
            job_description=job_description,
            job_title=job_title,
            company_name=company_name,
            tailoring_style=tailoring_style,
            focus_keywords=focus_keywords,
            custom_instructions=custom_instructions,
        )

        version = await resume_service.create_ai_version(
            db=db,
            resume_id=resume_id,
            user_id=user_id,
            structured_data=result.get("structured_data", {}),
            markdown_content=result.get("markdown", ""),
            job_id=job_id,
            prompt_version=result.get("_prompt_version", RESUME_PROMPT_VERSION),
            model_used=result.get("_model", "unknown"),
            label=label,
        )

        app_id = None
        if job_id:
            from app.applications.models import Application, ApplicationStatus
            app_res = await db.execute(
                select(Application).where(
                    Application.user_id == user_id,
                    Application.job_id == job_id
                )
            )
            app = app_res.scalar_one_or_none()
            if not app:
                app = Application(
                    user_id=user_id,
                    job_id=job_id,
                    resume_version_id=version.id,
                    status=ApplicationStatus.READY,
                    job_title_snapshot=job_title,
                    company_name_snapshot=company_name,
                )
                db.add(app)
            else:
                app.resume_version_id = version.id
                if app.status == ApplicationStatus.DRAFT:
                    app.status = ApplicationStatus.READY
            await db.commit()
            await db.refresh(app)
            app_id = app.id

        return {
            "version_id": version.id,
            "version_number": version.version_number,
            "markdown": result.get("markdown", ""),
            "generation_id": result.get("_generation_id"),
            "application_id": app_id,
        }

    # Style-specific prompt modifiers for resume tailoring
    _TAILORING_STYLES = {
        "ats_optimized": (
            "Focus: MAXIMUM ATS compatibility. Use exact keyword matches from the job description. "
            "Prioritize hard skills, certifications, and technology stacks. "
            "Use standard section headings (Experience, Skills, Education). Avoid creative formatting."
        ),
        "narrative": (
            "Focus: STORYTELLING approach. Write compelling narrative bullet points that demonstrate impact. "
            "Emphasize career progression, leadership stories, and measurable achievements. "
            "Use a professional but engaging tone that shows personality."
        ),
        "skills_focused": (
            "Focus: TECHNICAL SKILLS prominence. Lead with a comprehensive skills matrix. "
            "Group skills by category (languages, frameworks, tools, methodologies). "
            "Align skill descriptions with job requirements. Quantify proficiency where possible."
        ),
        "experience_focused": (
            "Focus: WORK EXPERIENCE depth. Expand on work experience with detailed bullet points. "
            "Emphasize responsibilities, team size, project scope, and business impact. "
            "Show career growth and increasing responsibility over time."
        ),
    }

    async def _generate_resume(
        self,
        db: AsyncSession,
        user_id: str,
        structured_resume: dict,
        job_description: str | None = None,
        job_title: str | None = None,
        company_name: str | None = None,
        provider: str = "gemini",
        tailoring_style: str = "ats_optimized",
        focus_keywords: list[str] | None = None,
        custom_instructions: str | None = None,
    ) -> dict:
        """Core resume generation: prompt → AI → parse → cache → audit."""
        context_parts = [
            f"Current Resume Data:\n{json.dumps(structured_resume, indent=2)}"
        ]
        if job_description:
            context_parts.append(f"Target Job Description:\n{job_description}")
        if job_title:
            context_parts.append(f"Target Role: {job_title}")
        if company_name:
            context_parts.append(f"Target Company: {company_name}")

        # Inject tailoring style
        style_directive = self._TAILORING_STYLES.get(tailoring_style, self._TAILORING_STYLES["ats_optimized"])

        # Inject focus keywords
        keyword_directive = ""
        if focus_keywords:
            keyword_directive = f"\nPRIORITY KEYWORDS to emphasize: {', '.join(focus_keywords)}\n"

        # Inject custom user instructions
        user_directive = ""
        if custom_instructions:
            user_directive = f"\nADDITIONAL USER INSTRUCTIONS: {custom_instructions}\n"

        system_prompt = (
            "You are an elite resume optimization and ATS (Applicant Tracking System) screening expert. "
            "Given a candidate's resume data and a target job description, "
            "produce an optimized version of the resume with an ATS Keyword Match Score analysis.\n\n"
            f"TAILORING STYLE: {style_directive}\n\n"
            f"{keyword_directive}"
            f"{user_directive}"
            "Rules:\n"
            "- NEVER invent experience, certifications, or skills the candidate doesn't have\n"
            "- Reorder and emphasize relevant sections and keywords matching the target role\n"
            "- Improve bullet points with strong action verbs and quantified metrics\n"
            "- Calculate a realistic ATS Keyword Match Score (0 to 100) comparing candidate skills vs job requirements\n\n"
            "IMPORTANT: You MUST return valid JSON (no markdown fences). The JSON object MUST have exactly two top-level keys:\n"
            '- "structured_data": a JSON object that MUST contain ALL of the following keys:\n'
            '    - "ats_score": integer 0-100 (REQUIRED, NEVER omit this field)\n'
            '    - "matched_keywords": array of strings — skills from the candidate that match the job (REQUIRED)\n'
            '    - "missing_skills": array of strings — job-required skills NOT in candidate profile (REQUIRED)\n'
            '    - "ats_feedback": string — brief explanation of ATS optimization quality\n'
            '    - "skills": array of strings — all candidate skills\n'
            '    - "summary": string — professional summary\n'
            '- "markdown": string — the full resume formatted as clean Markdown for display\n\n'
            'CRITICAL: "ats_score" is MANDATORY inside "structured_data". If you cannot calculate it precisely, '
            'estimate based on keyword overlap between the candidate skills and the job requirements. '
            'Do NOT wrap the JSON in markdown code fences.'
        )
        prompt = "\n\n".join(context_parts)

        # Check cache
        prompt_hash = hashlib.sha256(
            (prompt + system_prompt).encode("utf-8")
        ).hexdigest()
        cached = _prompt_cache.get_cached(prompt_hash)
        if cached:
            logger.info(f"AI Resume Cache Hit: {prompt_hash[:12]}")
            return cached

        # Select providers
        primary = gemini_provider if provider == "gemini" else groq_provider
        fallback = groq_provider if provider == "gemini" else gemini_provider

        def _fallback_factory() -> AIResponse:
            return AIResponse(
                content=json.dumps({
                    "structured_data": structured_resume,
                    "markdown": (
                        f"# Resume Tailored for {job_title or 'Target Role'} "
                        f"@ {company_name or 'Company'}\n\n"
                        f"## Professional Summary\nResults-driven engineer aligned "
                        f"with core requirements for {job_title or 'the target role'} "
                        f"at {company_name or 'the organization'}.\n\n"
                        f"## Key Skills & Qualifications\n"
                        f"- Software Engineering & Architecture\n"
                        f"- Full-Stack Web Development\n"
                        f"- Agile & Collaborative Problem Solving\n\n"
                        f"*(Generated via smart fallback system)*"
                    ),
                }),
                model="local-template-fallback",
                total_tokens=0,
                prompt_tokens=0,
                completion_tokens=0,
            )

        response = await self._call_with_fallback(
            primary, fallback, prompt, system_prompt, 0.4, _fallback_factory
        )

        generation = await self._log_generation(
            db=db,
            user_id=user_id,
            generation_type="resume",
            prompt_version=RESUME_PROMPT_VERSION,
            response=response,
            prompt=prompt,
            input_context={"has_job": bool(job_description)},
            temperature=0.4,
        )

        clean_text = _clean_llm_json(response.content)
        logger.info(f"AI Resume raw response length: {len(response.content)}, cleaned: {len(clean_text)}, starts with: {clean_text[:80]!r}")

        try:
            result = json.loads(clean_text)
            if isinstance(result, dict):
                sdata = result.get("structured_data")
                if not isinstance(sdata, dict):
                    sdata = {}
                    result["structured_data"] = sdata

                # Lift top-level ATS keys into structured_data if AI placed them at root
                for key in ["ats_score", "matched_keywords", "missing_skills", "ats_feedback"]:
                    if key in result and key not in sdata:
                        sdata[key] = result[key]

                # Flatten skills to string list (handles [{"name": "Python"}, ...] format)
                if "skills" in sdata:
                    sdata["skills"] = _flatten_skills(sdata["skills"])

                # Calculate real keyword match score if ats_score was omitted by LLM
                if ("ats_score" not in sdata or sdata["ats_score"] is None) and (job_description or job_title):
                    matched = sdata.get("matched_keywords", [])
                    missing = sdata.get("missing_skills", [])
                    if isinstance(matched, list) and isinstance(missing, list) and (matched or missing):
                        total = len(matched) + len(missing)
                        if total > 0:
                            sdata["ats_score"] = int((len(matched) / total) * 100)
                    
                    # Last resort: compute from candidate skills vs job text
                    if "ats_score" not in sdata or sdata["ats_score"] is None:
                        cand_skills = _flatten_skills(sdata.get("skills") or structured_resume.get("skills"))
                        job_text = f"{job_title or ''} {job_description or ''}".lower()
                        if cand_skills and job_text.strip():
                            matches = [s for s in cand_skills if s.lower() in job_text]
                            sdata["matched_keywords"] = matches
                            coverage = int((len(matches) / len(cand_skills)) * 100) if cand_skills else 0
                            sdata["ats_score"] = max(coverage, 55)  # Floor at 55% for tailored resumes

                logger.info(f"AI Resume parsed — ats_score={sdata.get('ats_score')}, matched={len(sdata.get('matched_keywords', []))}, missing={len(sdata.get('missing_skills', []))}")
        except json.JSONDecodeError as e:
            logger.error(f"AI Resume JSON parse failed: {e}. Raw content starts with: {clean_text[:200]!r}")
            result = {"structured_data": structured_resume, "markdown": response.content}

        result["_generation_id"] = generation.id
        result["_model"] = response.model
        result["_prompt_version"] = RESUME_PROMPT_VERSION

        _prompt_cache.put(prompt_hash, result)
        return result

    # ── Email Generation ──────────────────────────────────────

    async def generate_email_flow(
        self,
        db: AsyncSession,
        user_id: str,
        application_id: str,
        tone: str,
    ) -> dict:
        """Full orchestration: fetch app+job data → build resume context → generate email."""
        from app.resumes.models import Resume, ResumeVersion

        app = await application_service.get(
            db=db, app_id=application_id, user_id=user_id
        )
        job = await job_service.get_job(db=db, job_id=app.job_id, user_id=user_id)

        resume_summary = ""

        # 1. Try specific resume version attached to the application
        if app.resume_version_id:
            result = await db.execute(
                select(ResumeVersion).where(
                    ResumeVersion.id == app.resume_version_id
                )
            )
            rv = result.scalar_one_or_none()
            if rv:
                resume_summary = self._extract_resume_summary(rv.structured_data)

        # 2. Fallback to latest parsed resume
        if not resume_summary:
            res_result = await db.execute(
                select(Resume)
                .where(Resume.user_id == user_id)
                .order_by(Resume.created_at.desc())
            )
            latest_resume = res_result.scalars().first()
            if latest_resume:
                resume_summary = self._extract_resume_summary(
                    latest_resume.structured_data
                )
                if not resume_summary and latest_resume.raw_text:
                    resume_summary = latest_resume.raw_text[:1500]

        if not resume_summary:
            resume_summary = (
                "Experienced software engineer with background in tech "
                "and software development."
            )

        from app.auth.models import User
        u_res = await db.execute(select(User).where(User.id == user_id))
        user_obj = u_res.scalar_one_or_none()
        candidate_name = user_obj.full_name if user_obj and user_obj.full_name else "Candidate"

        result = await self._generate_email(
            db=db,
            user_id=user_id,
            candidate_name=candidate_name,
            resume_summary=resume_summary,
            job_title=job.title,
            company_name=job.company.name if job.company else "the company",
            tone=tone,
        )
        return {
            "subject": result.get("subject", ""),
            "body_text": result.get("body_text", ""),
            "body_html": result.get("body_html", ""),
            "generation_id": result.get("_generation_id"),
        }

    async def _generate_email(
        self,
        db: AsyncSession,
        user_id: str,
        resume_summary: str,
        job_title: str,
        company_name: str,
        candidate_name: str = "Candidate",
        contact_name: str | None = None,
        tone: str = "professional",
        provider: str = "groq",
    ) -> dict:
        """Core email generation: prompt → AI → parse → cache → audit."""
        tone_guidelines = {
            "professional": (
                "TONE: Professional\n"
                "- Formal but approachable. Use measured, confident language.\n"
                "- Structure: clear paragraphs, no emojis, no exclamation marks.\n"
                "- Use full sentences, avoid contractions (use 'I am' instead of 'I'm').\n"
                "- Opening: 'Dear [recipient]' or 'Hello [recipient]'.\n"
                "- Sign off with 'Kind regards' or 'Best regards'.\n"
                "- Voice: A confident professional reaching out about a role they are genuinely qualified for."
            ),
            "friendly": (
                "TONE: Friendly / Casual\n"
                "- Warm and conversational, like messaging a colleague or connection.\n"
                "- Use contractions freely (I'm, I'd, you'll). Keep sentences short and punchy.\n"
                "- One emoji max (in subject only). Light humor is welcome.\n"
                "- Opening: 'Hi [recipient]' or 'Hey [recipient]'.\n"
                "- Sign off with 'Cheers' or 'Looking forward to connecting!'.\n"
                "- Voice: A friendly, enthusiastic person who genuinely wants to connect."
            ),
            "enthusiastic": (
                "TONE: Enthusiastic\n"
                "- High energy, genuinely excited about the opportunity.\n"
                "- Use strong positive language ('thrilled', 'excited', 'passionate about').\n"
                "- Show deep passion for the company's mission, product, or recent achievements.\n"
                "- Keep it authentic — max 2 exclamation marks in the whole email.\n"
                "- Opening: 'Hi [recipient]!' or a hook about the company.\n"
                "- Sign off with 'Excited to connect!' or 'Can't wait to hear from you!'.\n"
                "- Voice: Someone who has been following the company and is genuinely pumped about this role."
            ),
            "concise": (
                "TONE: Concise / Direct\n"
                "- Ultra-brief. 3-5 sentences max for the ENTIRE body. Every word earns its place.\n"
                "- No pleasantries, no filler, no 'I hope this finds you well'.\n"
                "- Lead with your single strongest, most relevant achievement.\n"
                "- End with a direct, specific ask (e.g., '15 min call Thursday?').\n"
                "- Opening: Jump straight in — 'I saw the [role] at [company]...'\n"
                f"- Sign off with just your name: '— {candidate_name}'.\n"
                "- Voice: A busy, accomplished person who respects the reader's time."
            ),
            "formal": (
                "TONE: Formal\n"
                "- Highly structured and polished. Corporate-level communication.\n"
                "- Use full sentences, no contractions, proper salutations.\n"
                "- Reference the specific role and company by name.\n"
                "- Opening: 'Dear [recipient]' or 'Dear Hiring Manager'.\n"
                "- Sign off with 'Respectfully' or 'Sincerely'.\n"
                "- Voice: A cover letter from a top-tier professional. Structured, deliberate, impeccable."
            ),
        }
        tone_instruction = tone_guidelines.get(tone.lower(), tone_guidelines["professional"])

        system_prompt = (
            f"You are a career outreach strategist ghostwriting a cold email on behalf of '{candidate_name}'. "
            "The email MUST be written in FIRST PERSON (I, my, me) as if the candidate is writing it themselves.\n\n"
            "CRITICAL RULES:\n"
            f"1. You ARE '{candidate_name}'. Write as them. NEVER refer to '{candidate_name}' in third person.\n"
            "2. NEVER use bracketed placeholders like [Your Name], [Candidate Name], [Phone Number].\n"
            f"3. Sign off using the name '{candidate_name}'.\n"
            "4. NEVER write phrases like 'I am writing to recommend' or 'I'd like to introduce' — you ARE the person.\n\n"
            "OUTREACH FRAMEWORK:\n"
            "1. SUBJECT LINE: 3-8 words, specific to the role. NO clickbait, NO generic 'Application for...' subjects.\n"
            "   Good: 'Python engineer — 3 yrs distributed systems', 'Full-stack dev who scaled 10x'\n"
            "   Bad: 'Application for Software Engineer', 'Interested in the role'\n"
            "2. OPENING: One sentence — who I am and why this specific role at this specific company excites me. "
            "   Mention something specific about the company (product, mission, recent news) if possible.\n"
            "3. VALUE: 2-3 bullet points or short sentences highlighting MY quantified achievements from the resume. "
            "   Use specific numbers, technologies, and outcomes. Show impact, not just responsibilities.\n"
            "4. CTA: Low-friction ask — suggest a brief call, ask a thoughtful question, or offer to share more.\n"
            "5. CLOSING: Professional sign-off appropriate to the tone.\n"
            "6. NO FABRICATION: Only use facts from the candidate summary provided.\n\n"
            f"{tone_instruction}\n\n"
            "IMPORTANT: Return valid JSON (no markdown fences) with exactly these keys:\n"
            '- "subject": string — email subject line\n'
            '- "body_text": string — plain text email body (with proper line breaks)\n'
            '- "body_html": string — HTML formatted email body '
            "(use <strong> for key skills, <br> for line breaks, <p> for paragraphs)"
        )

        prompt = (
            f"Write a cold outreach email from me ({candidate_name}) to a recruiter/hiring manager.\n"
            f"I am applying for: {job_title}\n"
            f"At company: {company_name}\n"
            f"Send to: {contact_name or 'Hiring Team'}\n\n"
            f"My background summary:\n{resume_summary}"
        )

        # Check cache
        prompt_hash = hashlib.sha256(
            (prompt + system_prompt).encode("utf-8")
        ).hexdigest()
        cached = _prompt_cache.get_cached(prompt_hash)
        if cached:
            logger.info(f"AI Email Cache Hit: {prompt_hash[:12]}")
            return cached

        # Select providers
        primary = groq_provider if provider == "groq" else gemini_provider
        fallback = gemini_provider if provider == "groq" else groq_provider

        def _fallback_factory() -> AIResponse:
            return AIResponse(
                content=json.dumps({
                    "subject": f"Application for {job_title} role at {company_name}",
                    "body_text": (
                        f"Hi {contact_name or 'Hiring Team'},\n\n"
                        f"I am writing to express my interest in the {job_title} "
                        f"position at {company_name}.\n\n"
                        f"With my background in software engineering and technology "
                        f"development, I am confident in my ability to contribute "
                        f"effectively to your team.\n\n"
                        f"I would love the opportunity to connect and share more "
                        f"about my experience.\n\n"
                        f"Best regards,\nCandidate"
                    ),
                    "body_html": (
                        f"<p>Hi {contact_name or 'Hiring Team'},</p>"
                        f"<p>I am writing to express my interest in the "
                        f"<strong>{job_title}</strong> position at "
                        f"<strong>{company_name}</strong>.</p>"
                        f"<p>With my background in software engineering and technology "
                        f"development, I am confident in my ability to contribute "
                        f"effectively to your team.</p>"
                        f"<p>I would love the opportunity to connect and share more "
                        f"about my experience.</p>"
                        f"<p>Best regards,<br>Candidate</p>"
                    ),
                }),
                model="local-email-template-fallback",
                total_tokens=0,
                prompt_tokens=0,
                completion_tokens=0,
            )

        response = await self._call_with_fallback(
            primary, fallback, prompt, system_prompt, 0.6, _fallback_factory
        )

        generation = await self._log_generation(
            db=db,
            user_id=user_id,
            generation_type="email",
            prompt_version=EMAIL_PROMPT_VERSION,
            response=response,
            prompt=prompt,
            input_context={"job_title": job_title, "company": company_name},
            temperature=0.6,
        )

        clean_email_text = _clean_llm_json(response.content)
        try:
            result = json.loads(clean_email_text)
        except json.JSONDecodeError:
            logger.error(f"AI Email JSON parse failed. Raw starts with: {clean_email_text[:200]!r}")
            result = {
                "subject": f"Application for {job_title} at {company_name}",
                "body_text": response.content,
                "body_html": f"<p>{response.content}</p>",
            }

        result["_generation_id"] = generation.id
        _prompt_cache.put(prompt_hash, result)
        return result

    # ── Follow-up Email Generation ────────────────────────────

    async def generate_followup_flow(
        self,
        db: AsyncSession,
        user_id: str,
        conversation_id: str,
        follow_up_number: int = 1,
        tone: str = "professional",
    ) -> dict:
        """Generate a follow-up email for an existing conversation."""
        from app.email.models import Conversation, Message, MessageDirection

        # Fetch conversation and original message
        conv_result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        conversation = conv_result.scalar_one_or_none()
        if not conversation:
            raise ValueError("Conversation not found")

        # Get the original outbound message
        msg_result = await db.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.direction == MessageDirection.OUTBOUND,
            )
            .order_by(Message.created_at.asc())
        )
        messages = list(msg_result.scalars().all())
        if not messages:
            raise ValueError("No original message found in conversation")

        original_message = messages[0]
        original_subject = original_message.subject
        original_body = original_message.body_text or ""

        # Fetch job context from the application
        job_title = company_name = ""
        if conversation.application_id:
            from app.applications.models import Application
            app_result = await db.execute(
                select(Application).where(Application.id == conversation.application_id)
            )
            app = app_result.scalar_one_or_none()
            if app:
                job_title = app.job_title_snapshot or ""
                company_name = app.company_name_snapshot or ""

        # Get candidate name
        from app.auth.models import User
        u_res = await db.execute(select(User).where(User.id == user_id))
        user_obj = u_res.scalar_one_or_none()
        candidate_name = user_obj.full_name if user_obj and user_obj.full_name else "Candidate"

        result = await self._generate_followup_email(
            db=db,
            user_id=user_id,
            candidate_name=candidate_name,
            original_subject=original_subject,
            original_body=original_body,
            to_email=original_message.to_email,
            job_title=job_title,
            company_name=company_name,
            follow_up_number=follow_up_number,
            tone=tone,
        )
        return {
            "subject": result.get("subject", ""),
            "body_text": result.get("body_text", ""),
            "body_html": result.get("body_html", ""),
            "generation_id": result.get("_generation_id"),
            "follow_up_number": follow_up_number,
        }

    async def _generate_followup_email(
        self,
        db: AsyncSession,
        user_id: str,
        candidate_name: str,
        original_subject: str,
        original_body: str,
        to_email: str,
        job_title: str,
        company_name: str,
        follow_up_number: int = 1,
        tone: str = "professional",
    ) -> dict:
        """Core follow-up email generation with context-aware prompts."""
        # Adjust urgency based on follow-up number
        urgency_map = {
            1: (
                "CONTEXT: This is the FIRST follow-up (3-5 days after initial email). "
                "Tone: Gentle reminder, add a small new piece of value (a relevant insight, "
                "article, or additional achievement). Keep it SHORT — 3-4 sentences max. "
                "Reference the original email casually ('I wanted to follow up on my note last week...')."
            ),
            2: (
                "CONTEXT: This is the SECOND follow-up (7-10 days after initial email). "
                "Tone: Slightly more direct. Lead with a NEW value proposition or achievement not in the original email. "
                "Show you've done research on the company's recent news/product updates. "
                "Include a specific, low-friction CTA (e.g., '15-minute call this Thursday?')."
            ),
            3: (
                "CONTEXT: This is the THIRD follow-up (14+ days after initial email). "
                "Tone: Direct and concise — 'break-up' style. Acknowledge their busy schedule. "
                "Offer a final clear value statement and ask if it makes sense to connect, or if you should "
                "close the loop. This creates urgency without being pushy."
            ),
        }
        urgency = urgency_map.get(follow_up_number, urgency_map[3])

        system_prompt = (
            f"You are ghostwriting a follow-up cold email on behalf of '{candidate_name}'. "
            "Write in FIRST PERSON (I, my, me) as if the candidate is writing it themselves. "
            f"CRITICAL: Sign off using '{candidate_name}'. "
            "NEVER use bracketed placeholders like [Your Name]. "
            "NEVER refer to the candidate in third person.\n\n"
            f"{urgency}\n\n"
            "RULES:\n"
            "- Reference the original email naturally — the reader should know this is a follow-up\n"
            "- DO NOT repeat the same content from the original email\n"
            "- Add NEW value in each follow-up\n"
            "- Keep it shorter than the original email\n"
            "- Subject line should clearly be a follow-up (e.g., 'Re: ...' or 'Quick follow-up: ...')\n\n"
            "IMPORTANT: Return valid JSON (no markdown fences) with exactly these keys:\n"
            '- "subject": string — follow-up email subject line\n'
            '- "body_text": string — plain text email body\n'
            '- "body_html": string — HTML formatted email body'
        )

        prompt = (
            f"Generate follow-up #{follow_up_number} for:\n"
            f"Candidate: {candidate_name}\n"
            f"Role: {job_title}\n"
            f"Company: {company_name}\n"
            f"Recipient: {to_email}\n\n"
            f"Original Subject: {original_subject}\n"
            f"Original Email Body:\n{original_body[:2000]}"
        )

        # Check cache
        prompt_hash = hashlib.sha256(
            (prompt + system_prompt).encode("utf-8")
        ).hexdigest()
        cached = _prompt_cache.get_cached(prompt_hash)
        if cached:
            return cached

        primary = groq_provider
        fallback = gemini_provider

        def _fallback_factory() -> AIResponse:
            return AIResponse(
                content=json.dumps({
                    "subject": f"Re: {original_subject}",
                    "body_text": (
                        f"Hi,\n\n"
                        f"I wanted to follow up on my earlier message regarding the "
                        f"{job_title} role at {company_name}.\n\n"
                        f"I remain very interested in this opportunity and would welcome "
                        f"the chance to discuss how my background aligns with your team's needs.\n\n"
                        f"Would a brief call this week work for you?\n\n"
                        f"Best regards,\n{candidate_name}"
                    ),
                    "body_html": (
                        f"<p>Hi,</p>"
                        f"<p>I wanted to follow up on my earlier message regarding the "
                        f"<strong>{job_title}</strong> role at <strong>{company_name}</strong>.</p>"
                        f"<p>I remain very interested in this opportunity and would welcome "
                        f"the chance to discuss how my background aligns with your team's needs.</p>"
                        f"<p>Would a brief call this week work for you?</p>"
                        f"<p>Best regards,<br>{candidate_name}</p>"
                    ),
                }),
                model="local-followup-template-fallback",
                total_tokens=0,
                prompt_tokens=0,
                completion_tokens=0,
            )

        response = await self._call_with_fallback(
            primary, fallback, prompt, system_prompt, 0.6, _fallback_factory
        )

        generation = await self._log_generation(
            db=db,
            user_id=user_id,
            generation_type="followup_email",
            prompt_version=EMAIL_PROMPT_VERSION,
            response=response,
            prompt=prompt,
            input_context={
                "job_title": job_title,
                "company": company_name,
                "follow_up_number": follow_up_number,
            },
            temperature=0.6,
        )

        clean_text = _clean_llm_json(response.content)
        try:
            result = json.loads(clean_text)
        except json.JSONDecodeError:
            logger.error(f"AI Follow-up JSON parse failed. Raw: {clean_text[:200]!r}")
            result = {
                "subject": f"Re: {original_subject}",
                "body_text": response.content,
                "body_html": f"<p>{response.content}</p>",
            }

        result["_generation_id"] = generation.id
        _prompt_cache.put(prompt_hash, result)
        return result


ai_service = AIService()

