from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.employees import Employee
from app.core.security import verify_access_token


def get_current_employee(
    token_payload: dict = Depends(verify_access_token),
    db: Session = Depends(get_db)
) -> Employee:
    """
    Dependency to get the current authenticated employee from the database.
    Validates the bearer token and returns the Employee object.
    """
    emp_id = token_payload.get("sub")
    
    # Query the employee from database
    employee = db.query(Employee).filter(Employee.emp_id == int(emp_id)).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Employee not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return employee


def require_role(allowed_roles: list):
    """
    Dependency factory to check if employee has required role.
    Usage: Depends(require_role(["admin", "manager"]))
    """
    def role_checker(current_employee: Employee = Depends(get_current_employee)) -> Employee:
        if current_employee.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}"
            )
        return current_employee
    return role_checker

