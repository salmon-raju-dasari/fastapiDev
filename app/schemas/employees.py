from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any

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
                "password": "myPassword123"
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
    store_id: Optional[str] = Field(None, max_length=50)

class Employee(EmployeeBase):
    emp_id: int
    business_id: Optional[int] = None
    user_id: Optional[str] = None
    store_id: Optional[str] = None
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, obj):
        instance = super().from_orm(obj)
        instance.user_id = f"USR{obj.emp_id}"
        return instance

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

class VerifyOTPRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")

class ForgotPasswordOTPRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered email address")


