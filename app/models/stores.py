from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(String(100), ForeignKey("business.business_id"), nullable=False)
    store_sequence = Column(Integer, nullable=False)  # Sequence per business (1, 2, 3...)
    store_name = Column(String(200), nullable=False, index=True)
    store_address = Column(String(500))
    store_city = Column(String(100))
    store_state = Column(String(100))
    store_country = Column(String(100))
    store_pincode = Column(String(20))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship with business
    business = relationship("Business", backref="stores")
    
    # Composite unique constraint: store_name must be unique within a business
    __table_args__ = (
        UniqueConstraint('business_id', 'store_name', name='uq_business_store_name'),
    )
