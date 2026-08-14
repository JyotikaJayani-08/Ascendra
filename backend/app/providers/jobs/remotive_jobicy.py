"""
Ascendra — Remotive & Jobicy Free Job Providers.

100% free fallback job sources without rate limits or API key requirements.
"""

import logging
import httpx

from app.providers.jobs.base import JobProvider, NormalizedJob

logger = logging.getLogger("ascendra.providers.jobs.remotive_jobicy")


class RemotiveJobProvider(JobProvider):
    """Remotive free job API provider."""

    def __init__(self):
        self.url = "https://remotive.com/api/remote-jobs"

    @property
    def provider_name(self) -> str:
        return "remotive"

    async def fetch_jobs(self, **filters) -> list[NormalizedJob]:
        category = filters.get("category", "software-dev")
        query = filters.get("query", "")

        params = {}
        if category:
            params["category"] = category
        if query:
            params["search"] = query

        try:
            async with httpx.AsyncClient(verify=False) as client:
                res = await client.get(self.url, params=params, timeout=12.0)
                if res.status_code != 200:
                    return []

                data = res.json()
                raw_jobs = data.get("jobs", [])
                logger.info(f"Remotive retrieved {len(raw_jobs)} jobs")

                normalized = []
                for j in raw_jobs[:20]:
                    normalized.append(
                        NormalizedJob(
                            title=j.get("title", "Untitled"),
                            company_name=j.get("company_name", "Unknown"),
                            description=j.get("description"),
                            location=j.get("candidate_required_location") or "Remote",
                            remote_status="REMOTE",
                            employment_type=j.get("job_type") or "Full-time",
                            salary_currency=None,
                            source_url=j.get("url"),
                            external_id=str(j.get("id"))[:255],
                            provider_metadata={"category": j.get("category"), "salary_raw": j.get("salary")},
                        )
                    )
                return normalized
        except Exception as e:
            logger.warning(f"Remotive fetch error: {e}")
            return []


class JobicyProvider(JobProvider):
    """Jobicy free job API provider."""

    def __init__(self):
        self.url = "https://jobicy.com/api/v2/remote-jobs"

    @property
    def provider_name(self) -> str:
        return "jobicy"

    async def fetch_jobs(self, **filters) -> list[NormalizedJob]:
        count = filters.get("count", 20)
        query = filters.get("query", "")

        params = {"count": count}
        if query:
            params["geo"] = query

        try:
            async with httpx.AsyncClient(verify=False) as client:
                res = await client.get(self.url, params=params, timeout=12.0)
                if res.status_code != 200:
                    return []

                data = res.json()
                raw_jobs = data.get("jobs", [])
                logger.info(f"Jobicy retrieved {len(raw_jobs)} jobs")

                normalized = []
                for j in raw_jobs:
                    normalized.append(
                        NormalizedJob(
                            title=j.get("jobTitle", "Untitled"),
                            company_name=j.get("companyName", "Unknown"),
                            description=j.get("jobExcerpt") or j.get("jobDescription"),
                            location=j.get("jobGeo") or "Remote",
                            remote_status="REMOTE",
                            employment_type=j.get("jobType", "Full-time"),
                            salary_currency=None,
                            source_url=j.get("url"),
                            external_id=str(j.get("id"))[:255],
                            provider_metadata={"companyLogo": j.get("companyLogo"), "salary_raw": j.get("annualSalaryMin")},
                        )
                    )
                return normalized
        except Exception as e:
            logger.warning(f"Jobicy fetch error: {e}")
            return []


remotive_provider = RemotiveJobProvider()
jobicy_provider = JobicyProvider()
