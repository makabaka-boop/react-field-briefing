from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    project_code: str = Field(..., min_length=1, max_length=64)
    project_name: str = Field(..., min_length=1, max_length=255)
    owner_name: str = Field(..., min_length=1, max_length=128)


class ProjectCreate(ProjectBase):
    pass


class ProjectFromTemplate(BaseModel):
    project_code: str = Field(..., min_length=1, max_length=64)
    project_name: str = Field(..., min_length=1, max_length=255)
    owner_name: str = Field(..., min_length=1, max_length=128)
    template_id: int


class ProjectStatusUpdate(BaseModel):
    status: str
    actor: Optional[str] = "system"
    note: Optional[str] = ""


class Project(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    created_at: datetime


class SiteRiskSummary(BaseModel):
    site_id: int
    site_code: str
    site_name: str
    region: str
    total_findings: int
    unreviewed_count: int
    rejected_count: int
    highest_risk: str
    last_updated_at: Optional[str] = None


class ProjectRiskSummary(BaseModel):
    project_id: int
    project_code: str
    project_name: str
    total_sites: int
    total_findings: int
    unreviewed_count: int
    rejected_count: int
    highest_risk: str
    last_updated_at: Optional[str] = None
    sites: list[SiteRiskSummary]


class ProjectListItem(Project):
    site_count: int = 0
    highest_risk: str = "none"
    total_findings: int = 0
    unreviewed_count: int = 0
    rejected_count: int = 0
    last_updated_at: Optional[str] = None


class ProjectDetail(Project):
    site_count: int = 0
