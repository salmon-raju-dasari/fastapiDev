from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class BusinessBase(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=200, description="Business name (required)")
    business_type: Optional[str] = Field(None, max_length=100, description="Business type (optional)")
    category: Optional[str] = Field(None, max_length=100, description="Business category (optional)")
    owner_name: str = Field(..., min_length=1, max_length=100, description="Owner name (required)")
    phone_number: str = Field(..., min_length=1, max_length=20, description="Phone number (required)")
    email: EmailStr = Field(..., description="Email address (required)")
    gst_number: Optional[str] = Field(None, max_length=50, description="GST number (optional)")
    address: Optional[str] = Field(None, description="Business address (optional)")
    city: Optional[str] = Field(None, max_length=100, description="City (optional)")
    state: Optional[str] = Field(None, max_length=100, description="State (optional)")
    pincode: Optional[str] = Field(None, max_length=20, description="Pincode (optional)")
    country: Optional[str] = Field(None, max_length=100, description="Country (optional)")
    invoice_prefix: Optional[str] = Field(None, max_length=20, description="Invoice prefix (optional)")
    bank_account_number: Optional[str] = Field(None, max_length=50, description="Bank account number (optional)")
    ifsc_code: Optional[str] = Field(None, max_length=20, description="IFSC code (optional)")
    upi_id: Optional[str] = Field(None, max_length=100, description="UPI ID (optional)")

class BusinessCreate(BusinessBase):
    pass

class BusinessUpdate(BaseModel):
    business_name: Optional[str] = Field(None, min_length=1, max_length=200)
    business_type: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    owner_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, min_length=1, max_length=20)
    email: Optional[EmailStr] = None
    gst_number: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    invoice_prefix: Optional[str] = Field(None, max_length=20)
    bank_account_number: Optional[str] = Field(None, max_length=50)
    ifsc_code: Optional[str] = Field(None, max_length=20)
    upi_id: Optional[str] = Field(None, max_length=100)

class BusinessResponse(BaseModel):
    id: int
    business_id: str  # Auto-generated unique business ID
    business_name: str
    business_type: Optional[str] = None
    category: Optional[str] = None
    owner_name: str
    phone_number: str
    email: str
    gst_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: Optional[str] = None
    invoice_prefix: Optional[str] = None
    bank_account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    upi_id: Optional[str] = None
    has_logo: Optional[bool] = False  # Indicate if logo exists
    
    class Config:
        from_attributes = True
