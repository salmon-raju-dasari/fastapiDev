from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.orm import relationship
from app.database import Base

class EmployeeLabel(Base):
    """
    Employee Custom Labels Table
    Stores custom field labels and their possible values
    
    Two types of records:
    1. Template labels (emp_id = NULL): Store label names with array of predefined values for autocomplete
    2. Employee labels (emp_id NOT NULL): Store actual label-value pair for a specific employee
    
    For templates: label_name is unique per business_id, label_values stores array of options
    For employee data: one row per employee per label, label_value stores single selected value
    
    Note: Unique constraint for templates (business_id + label_name where emp_id IS NULL) 
    is created via partial index in migration script, not in model definition.
    """
    __tablename__ = "employee_labels"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    emp_id = Column(Integer, ForeignKey("employees.emp_id", ondelete="CASCADE"), nullable=True, index=True)
    business_id = Column(Integer, nullable=False, index=True)
    label_name = Column(String(100), nullable=False, index=True)
    label_value = Column(String(500), nullable=True)  # Single value for employee records
    label_values = Column(PG_ARRAY(String(500)), nullable=True)  # Array of values for template records
    
    # Relationship to Employee (optional since emp_id can be NULL for templates)
    employee = relationship("Employee", back_populates="labels")
    
    # Composite indexes for faster queries
    __table_args__ = (
        Index('idx_emp_business_label', 'emp_id', 'business_id', 'label_name'),
        Index('idx_business_label', 'business_id', 'label_name'),
    )
