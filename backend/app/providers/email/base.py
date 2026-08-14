"""
Ascendra — Email Provider ABC.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EmailMessage:
    to_email: str
    subject: str
    body_html: str
    body_text: str | None = None
    from_email: str | None = None
    from_name: str | None = None
    reply_to: str | None = None
    attachments: list[dict] | None = None


@dataclass
class SendResult:
    success: bool
    message_id: str | None = None
    error: str | None = None


class EmailProvider(ABC):
    """Abstract base for all email providers."""

    @abstractmethod
    async def send(self, message: EmailMessage) -> SendResult:
        """Send an email."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...
