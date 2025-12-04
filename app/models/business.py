from sqlalchemy import Column, Integer, String, Text, LargeBinary
from app.database import Base

class Business(Base):
    __tablename__ = "business"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    business_id = Column(String(50), unique=True, nullable=False, index=True)  # Stores employee business_id as string
    business_name = Column(String(200), nullable=False)
    business_type = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)
    owner_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False)
    email = Column(String(100), nullable=False)
    gst_number = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    invoice_prefix = Column(String(20), nullable=True)
    bank_account_number = Column(String(50), nullable=True)
    ifsc_code = Column(String(20), nullable=True)
    upi_id = Column(String(100), nullable=True)
    logo_data = Column(LargeBinary, nullable=True)  # Store logo image as binary
    logo_content_type = Column(String(50), nullable=True)  # Store MIME type
