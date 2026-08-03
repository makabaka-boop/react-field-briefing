from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SiteBase(BaseModel):
    site_code: str = Field(..., min_length=1, max_length=64)
    site_name: str = Field(..., min_length=1, max_length=255)
    address_text: Optional[str] = ""
    region: Optional[str] = ""


class SiteCreate(SiteBase):
    project_id: int


class SiteUpdate(BaseModel):
    site_name: Optional[str] = None
    address_text: Optional[str] = None
    region: Optional[str] = None


class Site(SiteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
