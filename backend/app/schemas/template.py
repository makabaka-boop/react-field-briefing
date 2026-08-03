from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class TemplateBase(BaseModel):
    template_name: str = Field(..., min_length=1, max_length=255)
    default_region: Optional[str] = ""
    site_items: list[dict[str, Any]] = Field(default_factory=list)


class TemplateCreate(TemplateBase):
    pass


class SiteTemplate(TemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
