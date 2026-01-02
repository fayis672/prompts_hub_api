from pydantic import BaseModel
from enum import Enum
from typing import Optional
from datetime import datetime
from uuid import UUID

class ReportableType(str, Enum):
    PROMPT = "prompt"
    COMMENT = "comment"
    USER = "user"

class ReportReason(str, Enum):
    SPAM = "spam"
    INAPPROPRIATE = "inappropriate"
    COPYRIGHT = "copyright"
    MISLEADING = "misleading"
    OTHER = "other"

class ReportStatus(str, Enum):
    PENDING = "pending"
    REVIEWING = "reviewing"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"

class ReportBase(BaseModel):
    reportable_type: ReportableType
    reportable_id: UUID
    reason: ReportReason
    description: Optional[str] = None

class ReportCreate(ReportBase):
    pass

class ReportUpdate(BaseModel):
    status: Optional[ReportStatus] = None
    reviewed_by: Optional[UUID] = None
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None

class ReportResponse(ReportBase):
    id: UUID
    reporter_id: UUID
    status: ReportStatus
    reviewed_by: Optional[UUID] = None
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
