"""
Ascendra — State Machine Engine.

Generic base class with concrete transition graphs for each domain entity.
Subclasses only need to define ALLOWED_TRANSITIONS — validation logic is inherited.
"""

from typing import ClassVar, Dict, Set

from app.core.exceptions import InvalidStateTransition


class StateMachine:
    """
    Abstract base for all state machines.

    Subclasses define ALLOWED_TRANSITIONS as a class variable mapping
    each state to its set of valid target states.
    """

    ALLOWED_TRANSITIONS: ClassVar[Dict[str, Set[str]]] = {}

    @classmethod
    def validate_transition(cls, current_status: str, target_status: str) -> None:
        """Validate if a transition from current_status to target_status is allowed."""
        if current_status == target_status:
            return

        current_upper = current_status.upper()
        target_upper = target_status.upper()

        allowed = cls.ALLOWED_TRANSITIONS.get(current_upper, set())
        if target_upper not in allowed:
            raise InvalidStateTransition(current_status, target_status)


class ApplicationStateMachine(StateMachine):
    """
    Strict state transitions for Application lifecycle.

    Per doc §28 — each status has a limited set of valid next states.
    """

    ALLOWED_TRANSITIONS: ClassVar[Dict[str, Set[str]]] = {
        "DRAFT": {"READY", "ARCHIVED", "WITHDRAWN"},
        "READY": {"RESUME_GENERATED", "DRAFT", "ARCHIVED", "WITHDRAWN"},
        "RESUME_GENERATED": {"EMAIL_GENERATED", "ARCHIVED", "WITHDRAWN"},
        "EMAIL_GENERATED": {"AWAITING_APPROVAL", "ARCHIVED", "WITHDRAWN"},
        "AWAITING_APPROVAL": {"QUEUED", "EMAIL_GENERATED", "ARCHIVED", "WITHDRAWN"},
        "QUEUED": {"SENT", "ARCHIVED"},
        "SENT": {"DELIVERED", "REPLY_RECEIVED", "REJECTED", "ARCHIVED"},
        "DELIVERED": {"REPLY_RECEIVED", "REJECTED", "ARCHIVED"},
        "REPLY_RECEIVED": {"INTERVIEW", "REJECTED", "ARCHIVED"},
        "INTERVIEW": {"OFFER", "REJECTED", "ARCHIVED"},
        "OFFER": {"ARCHIVED"},
        "REJECTED": {"ARCHIVED"},
        "WITHDRAWN": {"ARCHIVED"},
        "ARCHIVED": set(),
    }


class EmailStateMachine(StateMachine):
    """
    Strict state transitions for Email/Outreach lifecycle.
    """

    ALLOWED_TRANSITIONS: ClassVar[Dict[str, Set[str]]] = {
        "DRAFT": {"GENERATED", "EDITED", "APPROVED", "CLOSED"},
        "GENERATED": {"EDITED", "APPROVED", "QUEUED", "CLOSED"},
        "EDITED": {"APPROVED", "QUEUED", "CLOSED"},
        "APPROVED": {"QUEUED", "SENDING", "CLOSED"},
        "QUEUED": {"SENDING", "SENT", "FAILED", "CLOSED"},
        "SENDING": {"SENT", "FAILED", "CLOSED"},
        "SENT": {"DELIVERED", "REPLIED", "CLOSED"},
        "DELIVERED": {"REPLIED", "CLOSED"},
        "REPLIED": {"CLOSED"},
        "FAILED": {"QUEUED", "CLOSED"},
        "CLOSED": set(),
    }


class ResumeStateMachine(StateMachine):
    """
    State transitions for Resume lifecycle.

    UPLOADED → PARSING → PARSED → READY → ARCHIVED
    """

    ALLOWED_TRANSITIONS: ClassVar[Dict[str, Set[str]]] = {
        "UPLOADED": {"PARSING", "ARCHIVED"},
        "PARSING": {"PARSED", "PARSE_FAILED", "UPLOADED"},
        "PARSED": {"READY", "ARCHIVED"},
        "PARSE_FAILED": {"UPLOADED", "ARCHIVED"},
        "READY": {"ARCHIVED"},
        "ARCHIVED": set(),
    }


class ConversationStateMachine(StateMachine):
    """
    State transitions for Conversation lifecycle.

    CREATED → ACTIVE → WAITING → REPLIED → RESOLVED → ARCHIVED
    """

    ALLOWED_TRANSITIONS: ClassVar[Dict[str, Set[str]]] = {
        "CREATED": {"ACTIVE", "ARCHIVED"},
        "ACTIVE": {"WAITING", "REPLIED", "RESOLVED", "ARCHIVED"},
        "WAITING": {"REPLIED", "RESOLVED", "ARCHIVED"},
        "REPLIED": {"ACTIVE", "RESOLVED", "ARCHIVED"},
        "RESOLVED": {"ARCHIVED"},
        "ARCHIVED": set(),
    }

