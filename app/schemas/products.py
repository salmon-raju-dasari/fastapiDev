from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class ProductBase(BaseModel):
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Product name (1-100 characters)",
        examples=["Laptop", "Smart Phone"]
    )
    description: Optional[str] = Field(
        None, 
        max_length=255,
        description="Product description (optional, max 255 characters)"
    )
    price: float = Field(
        ..., 
        gt=0,
        description="Product price (must be greater than 0)",
        examples=[99.99, 1499.00]
    )
    quantity: int = Field(
        ..., 
        ge=0,
        description="Product quantity (must be 0 or greater)",
        examples=[100, 50]
    )
    category: Optional[str] = Field(
        None, 
        max_length=50,
        description="Product category (optional, max 50 characters)",
        examples=["Electronics", "Clothing"]
    )
    sku: str = Field(
        ..., 
        min_length=1, 
        max_length=50,
        description="Stock Keeping Unit - unique identifier (1-50 characters)",
        examples=["LAPTOP001", "PHONE-SM-001"]
    )
    
    @field_validator('name', 'sku')
    @classmethod
    def validate_not_empty(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f'{info.field_name} cannot be empty or whitespace only')
        return v.strip()
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('Price must be greater than 0')
        if v > 999999.99:
            raise ValueError('Price cannot exceed 999,999.99')
        # Round to 2 decimal places
        return round(v, 2)
    
    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if v < 0:
            raise ValueError('Quantity cannot be negative')
        if v > 1000000:
            raise ValueError('Quantity cannot exceed 1,000,000')
        return v
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "name": "Laptop",
                "description": "High-performance laptop for professionals",
                "price": 1499.99,
                "quantity": 50,
                "category": "Electronics",
                "sku": "LAPTOP001"
            }
        }

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=100,
        description="Product name (1-100 characters)"
    )
    description: Optional[str] = Field(
        None, 
        max_length=255,
        description="Product description (optional, max 255 characters)"
    )
    price: Optional[float] = Field(
        None, 
        gt=0,
        description="Product price (must be greater than 0)"
    )
    quantity: Optional[int] = Field(
        None, 
        ge=0,
        description="Product quantity (must be 0 or greater)"
    )
    category: Optional[str] = Field(
        None, 
        max_length=50,
        description="Product category (optional, max 50 characters)"
    )
    sku: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=50,
        description="New SKU (if updating SKU)"
    )
    
    @field_validator('name', 'sku')
    @classmethod
    def validate_not_empty(cls, v: Optional[str], info) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError(f'{info.field_name} cannot be empty or whitespace only')
        return v.strip() if v else v
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if v <= 0:
                raise ValueError('Price must be greater than 0')
            if v > 999999.99:
                raise ValueError('Price cannot exceed 999,999.99')
            return round(v, 2)
        return v
    
    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            if v < 0:
                raise ValueError('Quantity cannot be negative')
            if v > 1000000:
                raise ValueError('Quantity cannot exceed 1,000,000')
        return v
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "name": "Updated Laptop",
                "price": 1299.99,
                "quantity": 75
            }
        }

class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[str] = None
    
    class Config:
        from_attributes = True