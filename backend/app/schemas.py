from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ProjectCreate(BaseModel):
    project_code: str
    project_name: str
    owner_name: str
    status: Optional[str] = "draft"


class ProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    owner_name: Optional[str] = None
    status: Optional[str] = None


class Project(BaseModel):
    id: int
    project_code: str
    project_name: str
    owner_name: str
    status: str
    created_at: str


class ProjectFromTemplate(BaseModel):
    project_code: str
    project_name: str
    owner_name: str
    template_id: int
    status: Optional[str] = "draft"


class SiteCreate(BaseModel):
    site_code: str
    site_name: str
    address_text: Optional[str] = ""
    region: Optional[str] = ""
    project_id: int


class SiteUpdate(BaseModel):
    site_name: Optional[str] = None
    address_text: Optional[str] = None
    region: Optional[str] = None


class Site(BaseModel):
    id: int
    site_code: str
    site_name: str
    address_text: str
    region: str
    project_id: int


class SiteItem(BaseModel):
    site_code: str
    site_name: str
    address_text: Optional[str] = ""
    region: Optional[str] = ""


class FindingCreate(BaseModel):
    site_id: int
    category: Optional[str] = ""
    description: Optional[str] = ""
    risk_level: Optional[str] = "low"
    reported_by: Optional[str] = ""


class FindingUpdate(BaseModel):
    category: Optional[str] = None
    description: Optional[str] = None
    risk_level: Optional[str] = None
    reported_by: Optional[str] = None


class Finding(BaseModel):
    id: int
    site_id: int
    category: str
    description: str
    risk_level: str
    finding_status: str
    reported_by: str
    reported_at: str


class AttachmentCreate(BaseModel):
    file_name: str
    file_type: Optional[str] = ""
    storage_note: Optional[str] = ""
    linked_finding_id: Optional[int] = None


class Attachment(BaseModel):
    id: int
    file_name: str
    file_type: str
    storage_note: str
    linked_finding_id: Optional[int]
    created_at: str


class TemplateCreate(BaseModel):
    template_name: str
    default_region: Optional[str] = ""
    site_items: List[SiteItem] = []


class Template(BaseModel):
    id: int
    template_name: str
    default_region: str
    site_items: List[dict]


class ReviewCreate(BaseModel):
    reviewer_name: str
    conclusion: str
    comment: Optional[str] = ""
    new_status: Optional[str] = None


class Review(BaseModel):
    id: int
    finding_id: int
    reviewer_name: str
    conclusion: str
    comment: str
    reviewed_at: str


class StatusTransition(BaseModel):
    target_status: str
    actor: Optional[str] = ""


class AuditEvent(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    action: str
    actor: str
    details: dict
    created_at: str
