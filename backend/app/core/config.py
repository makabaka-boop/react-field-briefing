import os


class Settings:
    APP_NAME: str = "Field Briefing API"
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./field_briefing.db"
    )
    HOST: str = "0.0.0.0"
    PORT: int = 18111

    ALLOWED_STATUSES = (
        "draft",
        "submitted",
        "reviewing",
        "accepted",
        "rejected",
        "archived",
    )

    RISK_LEVELS = ("low", "medium", "high", "critical")


settings = Settings()
