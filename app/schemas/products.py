from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

class ProductBase(BaseModel):
    # Product Identification - Required
    productid: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=100,
        description="Unique product identifier (auto-generated if not provided)",
        examples=["PRD100", "PRD101"]
    )
    productname: str = Field(
        ..., 
        min_length=1, 
        max_length=500,
        description="Product name (1-500 characters)",
        examples=["Laptop Dell Inspiron 15", "Smart Phone Samsung Galaxy S24"]
    )
    barcode: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Product barcode (1-100 characters, required)",
        examples=["1234567890123", "EAN-13-1234567890"]
    )
    
    # Product Details
    sku: Optional[str] = Field(
        None, 
        max_length=100,
        description="Stock Keeping Unit (optional, max 100 characters)",
        examples=["LAPTOP001", "PHONE-SM-001"]
    )
    description: Optional[str] = Field(
        None, 
        max_length=2000,
        description="Product description (optional, max 2000 characters)"
    )
    brand: Optional[str] = Field(
        None, 
        max_length=100,
        description="Product brand (optional, max 100 characters)",
        examples=["Dell", "Samsung", "Apple"]
    )
    category: Optional[str] = Field(
        None, 
        max_length=100,
        description="Product category (optional, max 100 characters)",
        examples=["Electronics", "Clothing", "Food"]
    )
    
    # Images - Array of max 5 images
    productimages: Optional[List[str]] = Field(
        None,
        max_length=5,
        description="Array of product image URLs/paths (max 5 images)",
        examples=[["image1.jpg", "image2.jpg", "image3.jpg"]]
    )
    
    # Pricing & Units - Required
    price: Decimal = Field(
        ..., 
        gt=0,
        description="Product price with 2 decimal places (e.g., 100.00, 200.03)",
        examples=[99.99, 1499.00, 200.03]
    )
    unitvalue: Optional[int] = Field(
        None,
        description="Unit value in lakhs of rupees",
        examples=[1, 2, 5, 10]
    )
    unit: Optional[str] = Field(
        None,
        max_length=50,
        description="Unit of measurement (e.g., kg, liters, pieces)",
        examples=["kg", "liters", "pieces", "box"]
    )
    discount: Optional[int] = Field(
        0,
        ge=0,
        le=100,
        description="Discount percentage (0-100)",
        examples=[0, 10, 25, 50]
    )
    gst: Optional[int] = Field(
        0,
        ge=0,
        le=100,
        description="GST percentage (0-100)",
        examples=[0, 5, 12, 18, 28]
    )
    
    # Inventory
    openingstock: Optional[int] = Field(
        0,
        ge=0,
        description="Opening stock quantity",
        examples=[100, 500, 1000]
    )
    
    # Dates
    mfgdate: Optional[str] = Field(
        None,
        max_length=50,
        description="Manufacturing date (string format)",
        examples=["2024-01-15", "15-01-2024"]
    )
    expirydate: Optional[str] = Field(
        None,
        max_length=50,
        description="Expiry date (string format)",
        examples=["2025-01-15", "15-01-2025"]
    )
    
    # Supplier Information
    suppliername: Optional[str] = Field(
        None,
        max_length=100,
        description="Supplier name (max 100 characters)",
        examples=["ABC Suppliers", "XYZ Distributors"]
    )
    suppliercontact: Optional[str] = Field(
        None,
        max_length=100,
        description="Supplier contact (max 100 characters)",
        examples=["+91 9876543210", "supplier@example.com"]
    )
    
    # Custom Fields - Array of objects
    customfields: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Array of custom field objects",
        examples=[[{"field_name": "warranty", "field_value": "2 years"}, {"field_name": "color", "field_value": "black"}]]
    )
    
    @field_validator('productid', 'productname', 'barcode')
    @classmethod
    def validate_required_not_empty(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f'{info.field_name} cannot be empty or whitespace only')
        return v.strip()
    
    @field_validator('sku', 'brand', 'category', 'unit', 'suppliername', 'suppliercontact')
    @classmethod
    def validate_optional_not_empty(cls, v: Optional[str], info) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError(f'{info.field_name} cannot be empty or whitespace only if provided')
        return v.strip() if v else v
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError('Price must be greater than 0')
        if v > 9999999.99:
            raise ValueError('Price cannot exceed 9,999,999.99')
        # Round to 2 decimal places
        return round(v, 2)
    
    @field_validator('discount', 'gst')
    @classmethod
    def validate_percentage(cls, v: Optional[int], info) -> Optional[int]:
        if v is not None:
            if v < 0 or v > 100:
                raise ValueError(f'{info.field_name} must be between 0 and 100')
        return v
    
    @field_validator('openingstock', 'unitvalue')
    @classmethod
    def validate_non_negative(cls, v: Optional[int], info) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError(f'{info.field_name} cannot be negative')
        return v
    
    @field_validator('productimages')
    @classmethod
    def validate_images(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            if len(v) > 5:
                raise ValueError('Maximum 5 product images allowed')
            # Remove empty strings
            v = [img.strip() for img in v if img and img.strip()]
        return v if v else None
    
    @field_validator('customfields')
    @classmethod
    def validate_customfields(cls, v: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
        if v is not None:
            for field in v:
                if not isinstance(field, dict):
                    raise ValueError('Each custom field must be an object/dictionary')
        return v
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "productid": "PROD001",
                "productname": "Laptop Dell Inspiron 15",
                "barcode": "1234567890123",
                "sku": "LAPTOP001",
                "description": "High-performance laptop for professionals",
                "brand": "Dell",
                "category": "Electronics",
                "productimages": ["image1.jpg", "image2.jpg"],
                "price": 1499.99,
                "unitvalue": 1,
                "unit": "pieces",
                "discount": 10,
                "gst": 18,
                "openingstock": 50,
                "mfgdate": "2024-01-01",
                "expirydate": "2026-01-01",
                "suppliername": "ABC Suppliers",
                "suppliercontact": "+91 9876543210",
                "customfields": [{"warranty": "2 years"}, {"color": "black"}]
            }
        }

class ProductUpdate(BaseModel):
    # All fields are optional for updates
    productid: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=100,
        description="Product identifier (1-100 characters)"
    )
    productname: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=500,
        description="Product name (1-500 characters)"
    )
    barcode: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=100,
        description="Product barcode (1-100 characters)"
    )
    sku: Optional[str] = Field(
        None, 
        max_length=100,
        description="Stock Keeping Unit"
    )
    description: Optional[str] = Field(
        None, 
        max_length=2000,
        description="Product description"
    )
    brand: Optional[str] = Field(
        None, 
        max_length=100,
        description="Product brand"
    )
    category: Optional[str] = Field(
        None, 
        max_length=100,
        description="Product category"
    )
    productimages: Optional[List[str]] = Field(
        None,
        max_length=5,
        description="Array of product image URLs/paths (max 5)"
    )
    price: Optional[Decimal] = Field(
        None, 
        gt=0,
        description="Product price with 2 decimal places"
    )
    unitvalue: Optional[int] = Field(
        None,
        description="Unit value in lakhs"
    )
    unit: Optional[str] = Field(
        None,
        max_length=50,
        description="Unit of measurement"
    )
    discount: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Discount percentage"
    )
    gst: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="GST percentage"
    )
    openingstock: Optional[int] = Field(
        None,
        ge=0,
        description="Opening stock"
    )
    mfgdate: Optional[str] = Field(
        None,
        max_length=50,
        description="Manufacturing date"
    )
    expirydate: Optional[str] = Field(
        None,
        max_length=50,
        description="Expiry date"
    )
    suppliername: Optional[str] = Field(
        None,
        max_length=100,
        description="Supplier name"
    )
    suppliercontact: Optional[str] = Field(
        None,
        max_length=100,
        description="Supplier contact"
    )
    customfields: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Array of custom field objects"
    )
    
    @field_validator('productid', 'productname', 'barcode', 'sku', 'brand', 'category', 'unit', 'suppliername', 'suppliercontact')
    @classmethod
    def validate_not_empty(cls, v: Optional[str], info) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError(f'{info.field_name} cannot be empty or whitespace only if provided')
        return v.strip() if v else v
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            if v <= 0:
                raise ValueError('Price must be greater than 0')
            if v > 9999999.99:
                raise ValueError('Price cannot exceed 9,999,999.99')
            return round(v, 2)
        return v
    
    @field_validator('discount', 'gst')
    @classmethod
    def validate_percentage(cls, v: Optional[int], info) -> Optional[int]:
        if v is not None:
            if v < 0 or v > 100:
                raise ValueError(f'{info.field_name} must be between 0 and 100')
        return v
    
    @field_validator('openingstock', 'unitvalue')
    @classmethod
    def validate_non_negative(cls, v: Optional[int], info) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError(f'{info.field_name} cannot be negative')
        return v
    
    @field_validator('productimages')
    @classmethod
    def validate_images(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            if len(v) > 5:
                raise ValueError('Maximum 5 product images allowed')
            v = [img.strip() for img in v if img and img.strip()]
        return v if v else None
    
    @field_validator('customfields')
    @classmethod
    def validate_customfields(cls, v: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
        if v is not None:
            for field in v:
                if not isinstance(field, dict):
                    raise ValueError('Each custom field must be an object/dictionary')
        return v
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "productname": "Updated Laptop Name",
                "price": 1299.99,
                "discount": 15
            }
        }

class ProductResponse(BaseModel):
    id: int
    productid: str
    productname: str
    barcode: str
    sku: Optional[str] = None
    description: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    productimages: Optional[List[str]] = None
    price: Decimal
    unitvalue: Optional[int] = None
    unit: Optional[str] = None
    discount: Optional[int] = None
    gst: Optional[int] = None
    openingstock: Optional[int] = None
    quantity: Optional[int] = None
    mfgdate: Optional[str] = None
    expirydate: Optional[str] = None
    suppliername: Optional[str] = None
    suppliercontact: Optional[str] = None
    customfields: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[str] = None
    
    @model_validator(mode='after')
    def format_productid(self):
        """Format productid as PRD{id} if not already formatted"""
        if self.productid is None or self.productid == '':
            self.productid = f"PRD{self.id}"
        return self
    
    class Config:
        from_attributes = True