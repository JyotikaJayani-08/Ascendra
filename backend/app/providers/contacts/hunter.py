"""
Ascendra — Hunter.io Contact Provider.

Free tier: 25 requests/month (domain search) + 25 verifications/month.
"""

import logging
import re

import httpx

from app.config import settings
from app.providers.contacts.base import ContactProvider, DiscoveredContact

logger = logging.getLogger("ascendra.providers.contacts.hunter")

# Role-based email prefixes to filter out (not recruiting contacts)
_ROLE_BASED_PREFIXES = {
    "noreply", "no-reply", "info", "support", "admin", "webmaster",
    "contact", "hello", "sales", "billing", "help", "abuse",
    "postmaster", "mailer-daemon", "security",
    # Generic department addresses — often unmonitored or bounce
    "careers", "jobs", "hr", "recruiting", "recruitment", "talent",
    "apply", "applications", "hiring", "resume", "resumes",
}

# Basic email regex for format validation
_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def _is_valid_email_format(email: str) -> bool:
    """Check if an email has a valid format and isn't a role-based address."""
    if not email or len(email) < 6:
        return False
    if not _EMAIL_REGEX.match(email):
        return False
    local_part = email.split("@")[0].lower()
    if local_part in _ROLE_BASED_PREFIXES:
        return False
    return True


class HunterProvider(ContactProvider):

    @property
    def provider_name(self) -> str:
        return "hunter"

    async def _verify_email(self, email: str, client: httpx.AsyncClient) -> str:
        """
        Verify a single email via Hunter.io Email Verifier API.

        Returns verification result: 'deliverable', 'risky', 'undeliverable', or 'unknown'.
        Uses 1 verification credit per call.
        """
        try:
            response = await client.get(
                "https://api.hunter.io/v2/email-verifier",
                params={
                    "email": email,
                    "api_key": settings.HUNTER_API_KEY,
                },
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                result = data.get("data", {}).get("result", "unknown")
                status = data.get("data", {}).get("status", "unknown")
                logger.info(f"Hunter verify {email}: result={result}, status={status}")
                return result
            else:
                logger.warning(f"Hunter verify failed for {email}: HTTP {response.status_code}")
                return "unknown"
        except Exception as e:
            logger.warning(f"Hunter verify exception for {email}: {e}")
            return "unknown"

    async def find_contacts(
        self, company_name: str, company_domain: str | None = None
    ) -> list[DiscoveredContact]:
        """Find contacts via Hunter.io domain search with enhanced quality control."""
        if not settings.HUNTER_API_KEY:
            logger.warning("Hunter API key not configured")
            return []

        if not company_domain:
            logger.info(f"No domain for {company_name}, skipping Hunter")
            return []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.hunter.io/v2/domain-search",
                    params={
                        "domain": company_domain,
                        "api_key": settings.HUNTER_API_KEY,
                        "limit": 10,  # Fetch more to filter down to quality results
                    },
                    timeout=15,
                )
                response.raise_for_status()
                data = response.json()

                contacts = []
                for email_data in data.get("data", {}).get("emails", []):
                    email = email_data.get("value", "")
                    conf = email_data.get("confidence", 0)

                    # Step 1: Confidence threshold (increased from 75 to 80)
                    if conf < 80:
                        logger.info(f"Skipping low confidence email {email} (confidence: {conf}%)")
                        continue

                    # Step 2: Email format validation
                    if not _is_valid_email_format(email):
                        logger.info(f"Skipping invalid/role-based email: {email}")
                        continue

                    # Step 3: Verify emails with confidence 80-95% via Hunter API
                    # Emails with 96%+ confidence are trusted without extra verification
                    verification_result = "deliverable"  # Default for high-confidence
                    if conf < 96:
                        verification_result = await self._verify_email(email, client)
                        if verification_result in ("undeliverable", "risky"):
                            logger.info(f"Skipping {verification_result} email: {email} (verification: {verification_result})")
                            continue

                    contacts.append(DiscoveredContact(
                        full_name=f"{email_data.get('first_name', '')} {email_data.get('last_name', '')}".strip(),
                        email=email,
                        job_title=email_data.get("position"),
                        confidence=conf / 100,
                    ))

                logger.info(f"Hunter: found {len(contacts)} verified contacts for {company_domain}")
                return contacts

        except Exception as e:
            logger.error(f"Hunter search failed: {e}")
            return []


hunter_provider = HunterProvider()

