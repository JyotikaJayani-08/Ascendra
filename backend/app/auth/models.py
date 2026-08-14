"""
Ascendra — Auth Models.

User table mapped to Supabase auth.users.
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, Enum, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class UserStatus(str, enum.Enum):
    REGISTERED = "REGISTERED"
    EMAIL_PENDING = "EMAIL_PENDING"
    VERIFIED = "VERIFIED"
    PROFILE_INCOMPLETE = "PROFILE_INCOMPLETE"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DELETION_REQUESTED = "DELETION_REQUESTED"


class AuthProvider(str, enum.Enum):
    EMAIL = "EMAIL"
    GOOGLE = "GOOGLE"


class User(Base):
    __tablename__ = "users"

    # In Supabase, auth.users has id as UUID. We will use the same UUID.
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, index=True)
    
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    status: Mapped[str] = mapped_column(
        Enum(UserStatus, name="user_status"),
        nullable=False,
        default=UserStatus.ACTIVE,
    )
    auth_provider: Mapped[str] = mapped_column(
        Enum(AuthProvider, name="auth_provider"),
        nullable=False,
        default=AuthProvider.EMAIL,
    )
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Profile fields (nullable until profile is completed)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    email_configs: Mapped[list["UserEmailConfig"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.email} [{self.status}]>"


class EmailProviderType(str, enum.Enum):
    """Supported email provider types per doc/09 §110."""
    SMTP = "SMTP"                    # Generic SMTP (Gmail App Password, Outlook, Zoho, etc.)
    GMAIL_OAUTH = "GMAIL_OAUTH"      # Future: Gmail API OAuth 2.0
    OUTLOOK_OAUTH = "OUTLOOK_OAUTH"  # Future: Microsoft Graph OAuth 2.0


class UserEmailConfig(Base):
    """
    Per-user email provider connection (doc/09 §117, §121).

    Each user can configure their own SMTP credentials so emails
    are sent from their real email address. The global .env SMTP
    becomes the system fallback when no user config exists.

    Provider tokens are never exposed to the frontend.
    """
    __tablename__ = "user_email_configs"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    provider_type: Mapped[str] = mapped_column(
        Enum(EmailProviderType, name="email_provider_type"),
        nullable=False,
        default=EmailProviderType.SMTP,
    )
    # SMTP connection details
    smtp_host: Mapped[str] = mapped_column(String(255), nullable=False, default="smtp.gmail.com")
    smtp_port: Mapped[int] = mapped_column(Integer, nullable=False, default=587)
    smtp_username: Mapped[str] = mapped_column(String(320), nullable=False)
    smtp_password: Mapped[str] = mapped_column(String(512), nullable=False)  # App Password or credential
    # Display name used in "From:" header
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Whether this is the user's default sending config
    is_default: Mapped[bool] = mapped_column(Boolean, default=True)
    # Connection verified via test email
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # OAuth 2.0 token storage (Encrypted at rest)
    oauth_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    oauth_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    oauth_token_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    oauth_client_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    oauth_client_secret: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Relationship
    user: Mapped["User"] = relationship(back_populates="email_configs")

    def __repr__(self) -> str:
        return f"<UserEmailConfig {self.smtp_username} [{self.provider_type}]>"
