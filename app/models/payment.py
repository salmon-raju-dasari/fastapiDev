from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime
from app.database import Base

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)  # Owner's emp_id
    business_id = Column(Integer, nullable=False, index=True)  # Business ID (one payment per business)
    razorpay_order_id = Column(String(100), unique=True, nullable=False, index=True)
    razorpay_payment_id = Column(String(100), unique=True, nullable=True, index=True)
    razorpay_signature = Column(String(255), nullable=True)
    amount = Column(Integer, nullable=False)  # Amount in paise
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(String(20), default="created", nullable=False)  # created, paid, failed
    payment_method = Column(String(50), nullable=True)
    payment_email = Column(String(100), nullable=True)
    payment_contact = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    verified = Column(Boolean, default=False, nullable=False)
