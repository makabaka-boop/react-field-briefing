"""观察项（finding）状态机。

合法状态：draft, submitted, reviewing, accepted, rejected, archived
合法流转：
    draft -> submitted
    submitted -> reviewing
    reviewing -> accepted
    reviewing -> rejected
    accepted -> archived
    rejected -> archived
"""
from .errors import ApiError

STATUSES = ("draft", "submitted", "reviewing", "accepted", "rejected", "archived")

_ALLOWED = {
    "draft": ("submitted",),
    "submitted": ("reviewing",),
    "reviewing": ("accepted", "rejected"),
    "accepted": ("archived",),
    "rejected": ("archived",),
    "archived": (),
}


def can_transition(from_status, to_status):
    """判断 from_status -> to_status 是否为合法流转。"""
    return to_status in _ALLOWED.get(from_status, ())


def transition(from_status, to_status):
    """执行流转校验，非法时抛 ApiError(409, INVALID_STATE_TRANSITION)。"""
    if not can_transition(from_status, to_status):
        raise ApiError(
            409,
            "INVALID_STATE_TRANSITION",
            "illegal state transition: %s -> %s" % (from_status, to_status),
            {"from_status": from_status, "to_status": to_status},
        )
    return to_status
