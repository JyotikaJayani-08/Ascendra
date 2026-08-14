"""
Ascendra — Contact Provider ABC.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DiscoveredContact:
    full_name: str
    email: str | None = None
    job_title: str | None = None
    linkedin_url: str | None = None
    confidence: float = 0.5


class ContactProvider(ABC):

    @abstractmethod
    async def find_contacts(
        self, company_name: str, company_domain: str | None = None
    ) -> list[DiscoveredContact]:
        """Discover hiring contacts for a company."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...
