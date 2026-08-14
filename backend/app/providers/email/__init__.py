"""
Ascendra — Email Providers.

Exposes the core abstractions and concrete adapters for sending email.
"""

from app.providers.email.base import EmailMessage, EmailProvider, SendResult
from app.providers.email.custom_smtp import CustomSMTPProvider
from app.providers.email.gmail import GmailProvider
from app.providers.email.outlook import OutlookProvider

__all__ = [
    "EmailMessage",
    "EmailProvider",
    "SendResult",
    "CustomSMTPProvider",
    "GmailProvider",
    "OutlookProvider",
]
