"""
Ascendra — WeWorkRemotely Job Provider.

Free RSS/XML feed integration — no API key required.
"""

import logging
import xml.etree.ElementTree as ET
import httpx

from app.providers.jobs.base import JobProvider, NormalizedJob

logger = logging.getLogger("ascendra.providers.jobs.weworkremotely")

WWR_RSS_URL = "https://weworkremotely.com/remote-jobs.rss"


class WeWorkRemotelyProvider(JobProvider):

    @property
    def provider_name(self) -> str:
        return "weworkremotely"

    async def fetch_jobs(self, what: str | None = None, **filters) -> list[NormalizedJob]:
        """Fetch remote tech jobs from WeWorkRemotely RSS feed."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    WWR_RSS_URL,
                    headers={"User-Agent": "Ascendra/1.0"},
                    timeout=30,
                )
                response.raise_for_status()
                content = response.text

            root = ET.fromstring(content)
            channel = root.find("channel")
            if channel is None:
                return []

            jobs = []
            what_lower = what.lower().strip() if what else None

            for item in channel.findall("item"):
                title_text = item.findtext("title", "")
                link = item.findtext("link", "")
                description = item.findtext("description", "")
                guid = item.findtext("guid", link)

                if what_lower:
                    if what_lower not in title_text.lower() and what_lower not in description.lower():
                        continue

                # WWR titles are usually formatted as "Company Name: Job Title"
                company_name = "We Work Remotely"
                title = title_text
                if ":" in title_text:
                    parts = title_text.split(":", 1)
                    company_name = parts[0].strip()
                    title = parts[1].strip()

                jobs.append(NormalizedJob(
                    title=title,
                    company_name=company_name,
                    description=description,
                    location="Remote",
                    remote_status="REMOTE",
                    employment_type="FULL_TIME",
                    source_url=link,
                    external_id=guid,
                    provider_metadata={"platform": "WeWorkRemotely"},
                ))
                if len(jobs) >= 50:
                    break

            logger.info(f"WeWorkRemotely: fetched {len(jobs)} jobs for query: '{what}'")
            return jobs

        except Exception as e:
            logger.error(f"WeWorkRemotely fetch failed: {e}")
            return []


weworkremotely_provider = WeWorkRemotelyProvider()
