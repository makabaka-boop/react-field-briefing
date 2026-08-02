"""Small validation helpers used across handlers."""

from .errors import ValidationError


def require_fields(payload, fields):
    """Ensure required string fields exist and are non-empty after strip."""
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")
    missing = {}
    for field in fields:
        value = payload.get(field)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            missing[field] = "This field is required."
    if missing:
        raise ValidationError(
            "One or more required fields are missing.",
            details={"fields": missing},
        )


def clean_str(payload, field, required=False, default=None):
    value = payload.get(field, default)
    if value is None:
        if required:
            raise ValidationError(
                "One or more required fields are missing.",
                details={"fields": {field: "This field is required."}},
            )
        return default
    if not isinstance(value, str):
        raise ValidationError(
            "Field must be a string.", details={"field": field}
        )
    value = value.strip()
    if required and value == "":
        raise ValidationError(
            "One or more required fields are missing.",
            details={"fields": {field: "This field is required."}},
        )
    return value
