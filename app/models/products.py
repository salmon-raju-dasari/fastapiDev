from sqlalchemy import Column, Integer, String, DateTime, Numeric, BigInteger, JSON, ARRAY, LargeBinary
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY

from app.database import Base

class Products(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    business_id = Column(String(50), nullable=False, index=True)  # Links product to business
    
    # Product Identification
    productid = Column(String(100), unique=True, index=True, nullable=True)  # Auto-generated as PRD{id}
    productname = Column(String(500), nullable=False)
    barcode = Column(String(100), nullable=False, index=True)
    sku = Column(String(100), unique=True, index=True, nullable=True)
    
    # Product Details
    description = Column(String(2000), nullable=True)
    brand = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)
    
    # Images - Array of base64 image strings stored as JSON (max 5)
    productimages = Column(JSON, nullable=True)  # Stores array of base64 strings
    
    # Pricing & Units
    price = Column(Numeric(10, 2), nullable=False)  # Stores values like 00.00, 100.00, 200.03
    unitvalue = Column(BigInteger, nullable=True)  # Stores lakhs of rupees
    unit = Column(String(50), nullable=True)
    discount = Column(Integer, default=0, nullable=True)
    gst = Column(Integer, default=0, nullable=True)
    
    # Inventory
    openingstock = Column(BigInteger, default=0, nullable=True)
    quantity = Column(Integer, default=0)  # Keep for backward compatibility
    
    # Dates
    mfgdate = Column(String(50), nullable=True)
    expirydate = Column(String(50), nullable=True)
    
    # Supplier Information
    suppliername = Column(String(100), nullable=True)
    suppliercontact = Column(String(100), nullable=True)
    
    # Custom Fields - Array of objects
    customfields = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(String(50), nullable=True)
