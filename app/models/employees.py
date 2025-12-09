from sqlalchemy import Column, Integer, String, JSON, Sequence, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Employee(Base):
    __tablename__ = "employees"
    
    # Create a sequence that starts from 1000 for emp_id (only if not exists)
    emp_id_seq = Sequence('employee_emp_id_seq', start=1000, increment=1)
    emp_id = Column(
        Integer, 
        emp_id_seq,
        primary_key=True, 
        index=True,
        server_default=emp_id_seq.next_value()
    )
    
    # Create a sequence that starts from 20000 for business_id
    business_id_seq = Sequence('employee_business_id_seq', start=20000, increment=1)
    business_id = Column(
        Integer,
        business_id_seq,
        nullable=False,
        index=True,
        server_default=business_id_seq.next_value()
    )
    
    name = Column(String(100), index=True, nullable=False)
    email = Column(String(100), index=True, nullable=False)  # Not unique globally, unique per business
    phone_number = Column(String(20), nullable=False)
    aadhar_number = Column(String(12), nullable=True)
    address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    role = Column(String(50), nullable=False, default="employee")
    joining_date = Column(String(10), nullable=True)  # Stored as dd/mm/yyyy
    custom_fields = Column(JSON, nullable=True)  # Array of {labelname: labelvalue}
    hashed_password = Column(String(255), nullable=False)
    
    # Audit columns
    store_id = Column(String(50), nullable=True)
    created_by = Column(Integer, ForeignKey('employees.emp_id', ondelete='SET NULL'), nullable=True)
    updated_by = Column(Integer, ForeignKey('employees.emp_id', ondelete='SET NULL'), nullable=True)
    
    # Relationship to custom labels
    labels = relationship("EmployeeLabel", back_populates="employee", cascade="all, delete-orphan")
