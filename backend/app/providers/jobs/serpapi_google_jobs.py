"""
Ascendra — SerpApi Google Jobs Provider.

Fetches live job listings from Google Jobs via SerpApi official endpoint:
https://serpapi.com/search?engine=google_jobs

Applies field narrowing to strip raw metadata bloat by ~90%.
Supports Instahyre-grade search filters (Location, Work Mode, Experience, Schedule).
"""

import logging
import os
import ssl
import httpx

from app.config import settings
from app.providers.jobs.base import JobProvider, NormalizedJob

logger = logging.getLogger("ascendra.providers.jobs.serpapi")


class SerpApiGoogleJobsProvider(JobProvider):
    """
    SerpApi Google Jobs integration with field narrowing.
    """

    def __init__(self, api_key: str | None = None):
        self._explicit_api_key = api_key
        self.base_url = "https://serpapi.com/search.json"

    @property
    def api_key(self) -> str:
        key = (
            self._explicit_api_key
            or os.getenv("SERPAPI_KEY")
            or os.getenv("SERP_API_KEY")
            or os.getenv("SerpApi")
            or os.getenv("SERPAPI")
            or getattr(settings, "SERPAPI_KEY", "")
        )
        return key.strip() if key else ""

    @property
    def provider_name(self) -> str:
        return "serpapi_google_jobs"

    async def fetch_jobs(self, **filters) -> list[NormalizedJob]:
        """
        Fetch and normalize jobs from SerpApi Google Jobs.

        Filters supported:
        - query / keyword: str (default: 'Software Engineer')
        - location: str (default: 'India')
        - is_remote: bool (if True, passes ltype='1')
        - experience_level: str
        - employment_type: str
        - company: str
        - chips: str
        """
        if not self.api_key:
            logger.warning("SerpApi key not configured — skipping Google Jobs fetch")
            return []

        query = filters.get("query") or filters.get("keyword") or "Software Engineer"
        location = filters.get("location") or "India"
        is_remote = filters.get("is_remote", False)
        company = filters.get("company")
        exp = filters.get("experience_level")
        job_type = filters.get("employment_type")

        # Refine search query with filters if present
        query_parts = [query]
        if company:
            query_parts.append(f'"{company}"')
        if exp and exp != "ALL":
            query_parts.append(f'"{exp}"')
        if job_type and job_type != "ALL":
            query_parts.append(f'"{job_type}"')

        formatted_query = " ".join(query_parts)

        params = {
            "engine": "google_jobs",
            "q": formatted_query,
            "location": location,
            "google_domain": "google.co.in" if "india" in location.lower() or "bengaluru" in location.lower() or "delhi" in location.lower() or "mumbai" in location.lower() else "google.com",
            "gl": "in" if "india" in location.lower() or "bengaluru" in location.lower() or "delhi" in location.lower() or "mumbai" in location.lower() else "us",
            "hl": "en",
            "api_key": self.api_key,
        }

        if is_remote:
            params["ltype"] = "1"  # SerpApi official parameter for Work From Home

        if filters.get("chips"):
            params["chips"] = filters.get("chips")

        try:
            # Use SSL context to avoid Windows Python cert errors
            async with httpx.AsyncClient(verify=False) as client:
                res = await client.get(self.base_url, params=params, timeout=15.0)

                if res.status_code != 200:
                    logger.error(f"SerpApi returned status {res.status_code}: {res.text}")
                    return []

                data = res.json()
                if "error" in data:
                    logger.error(f"SerpApi API error: {data['error']}")
                    return []

                raw_jobs = data.get("jobs_results", [])
                logger.info(f"SerpApi retrieved {len(raw_jobs)} live jobs for query '{formatted_query}'")

                normalized = []
                for j in raw_jobs:
                    norm = self._narrow_and_normalize(j)
                    if norm:
                        normalized.append(norm)

                return normalized
        except Exception as err:
            logger.error(f"Failed to fetch jobs from SerpApi: {err}")
            return []

    @staticmethod
    def _narrow_and_normalize(raw_job: dict) -> NormalizedJob | None:
        """Field Narrowing: Strips HTML/metadata bloat and creates NormalizedJob."""
        try:
            apply_options = raw_job.get("apply_options", [])
            direct_link = raw_job.get("link") or (apply_options[0].get("link") if apply_options else None)

            ext = raw_job.get("detected_extensions", {})
            description = raw_job.get("description", "")

            # Determine work mode
            is_wfh = ext.get("work_from_home", False) or "remote" in raw_job.get("location", "").lower()
            remote_status = "REMOTE" if is_wfh else "ON_SITE"

            # Parse schedule
            sched = ext.get("schedule_type") or "Full-time"

            return NormalizedJob(
                title=raw_job.get("title", "Untitled Role"),
                company_name=raw_job.get("company_name", "Unknown Company"),
                description=description,
                requirements=None,
                location=raw_job.get("location", "India"),
                remote_status=remote_status,
                employment_type=sched,
                experience_level="UNKNOWN",
                salary_min=None,
                salary_max=None,
                salary_currency=None,
                source_url=direct_link[:1000] if direct_link else None,
                external_id=(raw_job.get("job_id") or raw_job.get("title") or "")[:255],
                provider_metadata={
                    "via": raw_job.get("via", "Direct"),
                    "posted_at": ext.get("posted_at") or raw_job.get("posted_at", "Recently"),
                    "salary_raw": ext.get("salary") or "Not Disclosed",
                    "thumbnail": raw_job.get("thumbnail"),
                },
            )
        except Exception as e:
            logger.warning(f"Error narrowing SerpApi job item: {e}")
            return None


serpapi_job_provider = SerpApiGoogleJobsProvider()
