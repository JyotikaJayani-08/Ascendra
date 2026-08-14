"""
Ascendra — Job Provider ABC.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class NormalizedJob:
    title: str
    company_name: str
    description: str | None = None
    requirements: str | None = None
    location: str | None = None
    remote_status: str = "UNKNOWN"
    employment_type: str = "UNKNOWN"
    experience_level: str = "UNKNOWN"
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    source_url: str | None = None
    external_id: str | None = None
    provider_metadata: dict = field(default_factory=dict)


class JobProvider(ABC):

    @abstractmethod
    async def fetch_jobs(self, **filters) -> list[NormalizedJob]:
        """Fetch and normalize jobs from the provider."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...
