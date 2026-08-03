from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ReviewBase(BaseModel):
    reviewer_name: str = Field(..., min_length=1, max_length=128)
    conclusion: str = Field(..., pattern="^(accepted|rejected)$")
    comment: Optional[str] = ""


class ReviewCreate(ReviewBase):
    finding_id: int


class Review(ReviewBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    finding_id: int
    reviewed_at: datetime
