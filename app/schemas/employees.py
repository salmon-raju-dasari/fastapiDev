from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class EmployeeLogin(BaseModel):
    user_id: str = Field(..., description="Employee user ID (format: USR1000)")
    password: str = Field(..., description="Employee password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "USR1000",
                "password": "myPassword123"
            }
        }

class EmployeeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Employee name (required, max 100 characters)")
    email: EmailStr = Field(..., description="Employee email address (required)")
    phone_number: str = Field(..., min_length=1, max_length=20, description="Phone number (required, max 20 characters)")
    aadhar_number: Optional[str] = Field(None, max_length=12, description="Aadhar number (optional, max 12 characters)")
    address: Optional[str] = Field(None, max_length=255, description="Address (optional)")
    city: Optional[str] = Field(None, max_length=100, description="City (optional)")
    state: Optional[str] = Field(None, max_length=100, description="State (optional)")
    country: Optional[str] = Field(None, max_length=100, description="Country (optional)")
    role: str = Field(..., description="Role of the employee (required)")
    joining_date: Optional[str] = Field(None, description="Joining date in dd/mm/yyyy format (optional)")
    custom_fields: Optional[List[Dict[str, str]]] = Field(None, description="Custom fields as array of {labelname: labelvalue}")
    store_id: Optional[int] = Field(None, description="Store ID (optional for owner, required for other roles)")

class EmployeeCreate(EmployeeBase):
    password: str = Field(
        min_length=8,
        description="Password (minimum 8 characters)",
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "phone_number": "1234567890",
                "aadhar_number": "123456789012",
                "address": "123 Main St",
                "city": "Mumbai",
                "state": "Maharashtra",
                "country": "India",
                "role": "employee",
                "joining_date": "01/01/2025",
                "custom_fields": [{"Emergency Contact": "9876543210"}, {"Blood Group": "O+"}],
                "password": "myPassword123",
                "store_id": 1
            }
        }

class EmployeeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, min_length=1, max_length=20)
    aadhar_number: Optional[str] = Field(None, max_length=12)
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = None
    joining_date: Optional[str] = None
    custom_fields: Optional[List[Dict[str, str]]] = None
    password: Optional[str] = Field(None, min_length=8)
    store_id: Optional[int] = None

class Employee(EmployeeBase):
    emp_id: int
    business_id: Optional[int] = None
    business_id_display: str = Field(default="", description="Formatted business ID (BUS20000, etc.)")
    user_id: Optional[str] = None
    store_id: Optional[int] = None
    store_id_display: Optional[str] = Field(None, description="Formatted store ID (STR1, STR2, etc.)")
    store_name: Optional[str] = Field(None, description="Store name")
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    avatar_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, obj):
        data = super().from_orm(obj)
        data.business_id_display = f"BUS{obj.business_id}"
        return data
    
    @model_validator(mode='before')
    @classmethod
    def extract_from_orm(cls, data):
        """Extract and transform data from ORM object"""
        
        # If data is an ORM object (has __dict__), extract attributes
        if hasattr(data, '__dict__'):
            obj = data
            result = {}
            
            # Copy all basic fields
            for field_name in ['emp_id', 'business_id', 'store_id', 'created_by', 'updated_by',
                              'name', 'email', 'phone_number', 'aadhar_number', 'address',
                              'city', 'state', 'country', 'role', 'joining_date', 
                              'avatar_url', 'thumbnail_url']:
                if hasattr(obj, field_name):
                    result[field_name] = getattr(obj, field_name)
            
            # Generate user_id
            if hasattr(obj, 'emp_id'):
                result['user_id'] = f"USR{obj.emp_id}"
            
            # Load custom_fields from labels relationship or direct field
            if hasattr(obj, 'labels') and obj.labels:
                result['custom_fields'] = [
                    {label.label_name: label.label_value} 
                    for label in obj.labels
                ]
            elif hasattr(obj, 'custom_fields'):
                result['custom_fields'] = obj.custom_fields
            else:
                result['custom_fields'] = []
            
            return result
        
        # If already a dict, return as is
        return data

class TokenWithRefresh(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class EmployeePaginatedResponse(BaseModel):
    items: List[Employee]
    total: int
    page: int
    page_size: int

class OwnerRegistration(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Owner name (required)")
    email: EmailStr = Field(..., description="Owner email address (required)")
    phone_number: str = Field(..., min_length=1, max_length=20, description="Phone number (required)")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    confirm_password: str = Field(..., min_length=8, description="Confirm password (minimum 8 characters)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Owner",
                "email": "owner@example.com",
                "phone_number": "1234567890",
                "password": "securePassword123",
                "confirm_password": "securePassword123"
            }
        }

class ForgotPasswordRequest(BaseModel):
    user_id: str = Field(..., description="User ID (format: USR1000)")
    email: EmailStr = Field(..., description="Registered email address")

class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Password reset token")
    user_id: str = Field(..., description="User ID")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")
    confirm_password: str = Field(..., min_length=8, description="Confirm new password")

class ForgotUsernameRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered email address")
    business_id: Optional[int] = Field(None, description="Business ID (optional - filter results to specific business)")

class VerifyOTPRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")

class ForgotPasswordOTPRequest(BaseModel):
    user_id: str = Field(..., description="User ID (format: USR1000)")
    email: EmailStr = Field(..., description="Registered email address")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=6, description="New password (min 6 characters)")

