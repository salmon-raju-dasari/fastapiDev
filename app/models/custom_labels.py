from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.sql import func
from app.database import Base

class CustomLabel(Base):
    """
    Custom Labels Table
    Stores custom label definitions with their predefined values for a business.
    Used for autocomplete/dropdown options when adding custom fields to employees and products.
    
    Example: Label "Blood Group" with values ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
    """
    __tablename__ = "custom_labels"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    label_name = Column(String(100), nullable=False, index=True)
    label_values = Column(PG_ARRAY(String(500)), nullable=False)  # Array of predefined values
    label_type = Column(String(50), nullable=False, default="employee", index=True)  # 'employee' or 'product'
    business_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Indexes and constraints
    __table_args__ = (
        # Unique constraint: one label name per business and type
        Index('idx_business_label_name_type', 'business_id', 'label_name', 'label_type', unique=True),
    )
