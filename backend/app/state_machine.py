from .errors import StateTransitionError

VALID_STATUSES = {"draft", "submitted", "reviewing", "accepted", "rejected", "archived"}

PROJECT_TRANSITIONS = {
    "draft": ["submitted", "archived"],
    "submitted": ["reviewing", "draft", "archived"],
    "reviewing": ["accepted", "rejected", "archived"],
    "accepted": ["archived"],
    "rejected": ["draft", "archived"],
    "archived": ["draft"],
}

FINDING_TRANSITIONS = {
    "draft": ["submitted", "archived"],
    "submitted": ["reviewing", "draft", "archived"],
    "reviewing": ["accepted", "rejected", "archived"],
    "accepted": ["archived"],
    "rejected": ["draft", "archived"],
    "archived": ["draft"],
}


def validate_status(status: str):
    if status not in VALID_STATUSES:
        from .errors import ValidationError
        raise ValidationError(
            f"Invalid status: {status}",
            {"allowed": sorted(VALID_STATUSES)},
        )


def transition_project(current: str, target: str):
    validate_status(current)
    validate_status(target)
    allowed = PROJECT_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise StateTransitionError(current, target, allowed)
    return target


def transition_finding(current: str, target: str):
    validate_status(current)
    validate_status(target)
    allowed = FINDING_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise StateTransitionError(current, target, allowed)
    return target
