from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class StoreBase(BaseModel):
    store_name: str = Field(..., min_length=1, max_length=200, description="Store name (required)")
    store_address: Optional[str] = Field(None, max_length=500, description="Store address")
    store_city: Optional[str] = Field(None, max_length=100, description="Store city")
    store_state: Optional[str] = Field(None, max_length=100, description="Store state")
    store_country: Optional[str] = Field(None, max_length=100, description="Store country")
    store_pincode: Optional[str] = Field(None, max_length=20, description="Store pincode")

class StoreCreate(StoreBase):
    pass

class StoreUpdate(BaseModel):
    store_name: Optional[str] = Field(None, min_length=1, max_length=200)
    store_address: Optional[str] = Field(None, max_length=500)
    store_city: Optional[str] = Field(None, max_length=100)
    store_state: Optional[str] = Field(None, max_length=100)
    store_country: Optional[str] = Field(None, max_length=100)
    store_pincode: Optional[str] = Field(None, max_length=20)

class StoreResponse(StoreBase):
    id: int
    store_id: str
    business_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
