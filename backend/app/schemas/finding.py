from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["low", "medium", "high", "critical"]


class FindingBase(BaseModel):
    category: str = Field(..., min_length=1, max_length=128)
    description: str = Field(..., min_length=1)
    risk_level: RiskLevel
    reported_by: str = Field(..., min_length=1, max_length=128)


class FindingDraftCreate(FindingBase):
    site_id: int


class FindingDraftUpdate(BaseModel):
    category: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None, min_length=1)
    risk_level: Optional[RiskLevel] = None
    reported_by: Optional[str] = Field(None, min_length=1, max_length=128)


class FindingSubmit(BaseModel):
    actor: str = Field(..., min_length=1)
    note: Optional[str] = ""


class FindingStatusUpdate(BaseModel):
    status: str
    actor: str = Field(..., min_length=1)
    note: Optional[str] = ""


class Finding(FindingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    finding_status: str
    reported_at: datetime
