from __future__ import annotations

from app.core.config import settings
from app.core.errors import InvalidStatusTransitionError


class StatusMachine:
    PROJECT_TRANSITIONS = {
        "draft": {"submitted", "archived"},
        "submitted": {"reviewing", "rejected", "archived"},
        "reviewing": {"accepted", "rejected", "archived"},
        "accepted": {"archived"},
        "rejected": {"draft", "archived"},
        "archived": set(),
    }

    FINDING_TRANSITIONS = {
        "draft": {"submitted", "archived"},
        "submitted": {"reviewing", "rejected", "archived"},
        "reviewing": {"accepted", "rejected", "archived"},
        "accepted": {"archived"},
        "rejected": {"draft", "archived"},
        "archived": set(),
    }

    @classmethod
    def validate(cls, current_status: str, new_status: str, kind: str = "project") -> None:
        if current_status not in settings.ALLOWED_STATUSES:
            raise InvalidStatusTransitionError(
                f"Unknown current status: {current_status}"
            )
        if new_status not in settings.ALLOWED_STATUSES:
            raise InvalidStatusTransitionError(
                f"Unknown target status: {new_status}"
            )
        transitions = (
            cls.PROJECT_TRANSITIONS if kind == "project" else cls.FINDING_TRANSITIONS
        )
        allowed = transitions.get(current_status, set())
        if new_status not in allowed:
            raise InvalidStatusTransitionError(
                f"Cannot transition from '{current_status}' to '{new_status}'"
            )

    @classmethod
    def can_transition(cls, current_status: str, new_status: str, kind: str = "project") -> bool:
        try:
            cls.validate(current_status, new_status, kind)
            return True
        except InvalidStatusTransitionError:
            return False
