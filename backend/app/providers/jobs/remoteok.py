"""
Ascendra — RemoteOK Job Provider.

Free, no API key required.
"""

import logging

import httpx

from app.providers.jobs.base import JobProvider, NormalizedJob

logger = logging.getLogger("ascendra.providers.jobs.remoteok")

REMOTEOK_API = "https://remoteok.com/api"


class RemoteOKProvider(JobProvider):

    @property
    def provider_name(self) -> str:
        return "remoteok"

    async def fetch_jobs(self, what: str | None = None, **filters) -> list[NormalizedJob]:
        """Fetch remote jobs from RemoteOK."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    REMOTEOK_API,
                    headers={"User-Agent": "Ascendra/1.0"},
                    timeout=30,
                )
                response.raise_for_status()
                response.encoding = "utf-8"
                data = response.json()

            jobs = []
            what_lower = what.lower().strip() if what else None

            # First item is metadata, skip it
            for item in data[1:]:
                title = item.get("position", "Unknown")
                company = item.get("company", "Unknown")
                description = item.get("description", "")
                tags = item.get("tags", [])

                if what_lower:
                    title_match = what_lower in title.lower()
                    desc_match = what_lower in description.lower()
                    tag_match = any(what_lower in str(t).lower() for t in tags if t)
                    if not (title_match or desc_match or tag_match):
                        continue

                jobs.append(NormalizedJob(
                    title=title,
                    company_name=company,
                    description=description,
                    location=item.get("location") or "Remote",
                    remote_status="REMOTE",
                    employment_type="FULL_TIME",
                    source_url=item.get("url", ""),
                    external_id=str(item.get("id", "")),
                    provider_metadata={"tags": tags},
                ))
                if len(jobs) >= 50:
                    break

            logger.info(f"RemoteOK: fetched {len(jobs)} jobs for query: '{what}'")
            return jobs

        except Exception as e:
            logger.error(f"RemoteOK fetch failed: {e}")
            return []


remoteok_provider = RemoteOKProvider()
