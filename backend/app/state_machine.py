"""Status definitions and transition rules shared by projects and findings.

The system uses a single vocabulary of statuses across projects and
observation findings so that reviewers see consistent lifecycle language:
    draft -> submitted -> reviewing -> accepted | rejected -> archived
"""

from .errors import InvalidTransitionError, ValidationError

DRAFT = "draft"
SUBMITTED = "submitted"
REVIEWING = "reviewing"
ACCEPTED = "accepted"
REJECTED = "rejected"
ARCHIVED = "archived"

ALL_STATUSES = (DRAFT, SUBMITTED, REVIEWING, ACCEPTED, REJECTED, ARCHIVED)

# Allowed transitions. A status may move only to the successors listed here.
_TRANSITIONS = {
    DRAFT: {SUBMITTED, ARCHIVED},
    SUBMITTED: {REVIEWING, REJECTED, ARCHIVED},
    REVIEWING: {ACCEPTED, REJECTED, ARCHIVED},
    ACCEPTED: {ARCHIVED},
    REJECTED: {DRAFT, ARCHIVED},
    ARCHIVED: set(),
}

RISK_LEVELS = ("low", "medium", "high", "critical")
_RISK_WEIGHT = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def validate_status(status):
    if status not in ALL_STATUSES:
        raise ValidationError(
            "Unknown status value.",
            details={"status": status, "allowed": list(ALL_STATUSES)},
        )
    return status


def validate_risk_level(risk_level):
    if risk_level not in RISK_LEVELS:
        raise ValidationError(
            "Unknown risk_level value.",
            details={"risk_level": risk_level, "allowed": list(RISK_LEVELS)},
        )
    return risk_level


def risk_weight(risk_level):
    return _RISK_WEIGHT.get(risk_level, 0)


def can_transition(current, target):
    return target in _TRANSITIONS.get(current, set())


def ensure_transition(current, target):
    """Validate a status change, raising on unknown or illegal transitions."""
    validate_status(current)
    validate_status(target)
    if current == target:
        raise InvalidTransitionError(
            "Status is already set to the requested value.",
            details={"current": current, "target": target},
        )
    if not can_transition(current, target):
        raise InvalidTransitionError(
            "Status transition is not allowed.",
            details={
                "current": current,
                "target": target,
                "allowed": sorted(_TRANSITIONS.get(current, set())),
            },
        )
    return target
