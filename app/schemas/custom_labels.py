from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class CustomLabelCreate(BaseModel):
    """Schema for creating a custom label"""
    label_name: str = Field(..., min_length=1, max_length=100, description="Name of the custom label")
    label_values: List[str] = Field(..., min_items=1, description="Array of predefined values for this label")

class CustomLabelUpdate(BaseModel):
    """Schema for updating a custom label"""
    label_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Updated name of the custom label")
    label_values: List[str] = Field(..., min_items=1, description="Array of predefined values for this label")

class CustomLabel(BaseModel):
    """Schema for custom label response"""
    id: int
    label_name: str
    label_values: List[str]
    business_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
