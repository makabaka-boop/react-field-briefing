from pydantic import BaseModel, ConfigDict, Field


class AttachmentBase(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=255)
    file_type: str = Field("", max_length=128)
    storage_note: str = ""


class AttachmentCreate(AttachmentBase):
    linked_finding_id: int


class Attachment(AttachmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    linked_finding_id: int
