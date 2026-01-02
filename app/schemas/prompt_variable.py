from pydantic import BaseModel, Field
from typing import Optional, List, Any
from enum import Enum
from datetime import datetime
from uuid import UUID

class VariableDataType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    SELECT = "select"
    MULTILINE = "multiline"
    BOOLEAN = "boolean"

class PromptVariableBase(BaseModel):
    variable_name: str = Field(..., max_length=100)
    variable_key: str = Field(..., max_length=100)
    description: Optional[str] = None
    default_value: Optional[str] = None
    data_type: VariableDataType = VariableDataType.TEXT
    is_required: bool = False
    display_order: int = 0
    
    options: Optional[List[Any]] = None

class PromptVariableCreate(PromptVariableBase):
    prompt_id: UUID

class PromptVariableCreateRequest(PromptVariableBase):
    pass

class PromptVariableUpdate(BaseModel):
    variable_name: Optional[str] = Field(None, max_length=100)
    variable_key: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    default_value: Optional[str] = None
    data_type: Optional[VariableDataType] = None
    is_required: Optional[bool] = None
    display_order: Optional[int] = None
    options: Optional[List[Any]] = None

class PromptVariableResponse(PromptVariableBase):
    id: UUID
    prompt_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
