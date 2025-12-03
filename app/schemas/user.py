from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional

class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "myPassword123"
            }
        }

class UserBase(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(
        min_length=3,
        max_length=50,
        description="Username (3-50 characters)"
    )
    full_name: Optional[str] = Field(
        None,
        max_length=100,
        description="User's full name (optional, max 100 characters)"
    )
    role: str = Field(
        description="Role of the user"
    )

class UserCreate(UserBase):
    password: str = Field(
        min_length=8,
        description="Password (minimum 8 characters)",
        examples=["myPassword123", "SecurePass456!"],
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "password": "myPassword123",
                "full_name": "John Doe"
            }
        }

class User(UserBase):
    id: int
    
    class Config:
        from_attributes = True  # Updated from orm_mode=True for newer Pydantic versions


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenWithRefresh(Token):
    refresh_token: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str

    class Config:
        json_schema_extra = {
            "example": {"refresh_token": "<your_refresh_token_here>"}
        }


class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None