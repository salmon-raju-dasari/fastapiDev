from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging
from app.database import get_db
from app.models.employees import Employee
from app.models.business import Business
from app.schemas.employees import (
    EmployeeCreate, 
    Employee as EmployeeSchema, 
    EmployeeUpdate,
    EmployeeLogin, 
    TokenWithRefresh, 
    RefreshTokenRequest,
    EmployeePaginatedResponse,
    OwnerRegistration,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ForgotUsernameRequest,
    VerifyOTPRequest,
    ForgotPasswordOTPRequest
)
from app.core.security import create_access_token, create_refresh_token, decode_token, is_refresh_token
from app.core.dependencies import get_current_employee, require_role
from passlib.context import CryptContext
from app.utils.email_service import send_registration_email, send_password_reset_email, send_otp_email, send_credentials_email
from app.utils.otp_service import store_otp, verify_otp

router = APIRouter()
logging.basicConfig(level=logging.INFO)

pwd_context = CryptContext(
    schemes=["argon2"],
    default="argon2",
    deprecated="auto",
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


@router.post("/register-owner", response_model=EmployeeSchema, status_code=status.HTTP_201_CREATED)
async def register_owner(
    owner_data: OwnerRegistration,
    db: Session = Depends(get_db)
):
    """Public endpoint to register an owner of the business"""
    try:
        # Check if email already exists
        existing_employee = db.query(Employee).filter(Employee.email == owner_data.email).first()
        if existing_employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already registered. Please use a different email or use the forgot password option."
            )
        
        # Validate password match
        if owner_data.password != owner_data.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match"
            )
        
        # Hash password
        try:
            logging.info(f"Creating owner account for {owner_data.name}")
            hashed_password = pwd_context.hash(owner_data.password)
        except Exception as e:
            logging.error(f"Error hashing password: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing password: {str(e)}"
            )
        
        # Create owner employee record
        db_owner = Employee(
            name=owner_data.name,
            email=owner_data.email,
            phone_number=owner_data.phone_number,
            role="owner",
            hashed_password=hashed_password
        )
        
        db.add(db_owner)
        db.commit()
        db.refresh(db_owner)
        
        # Create a Business record with the business_id and owner details
        business_record = Business(
            business_id=str(db_owner.business_id),
            business_name="",
            owner_name=owner_data.name,
            phone_number=owner_data.phone_number,
            email=owner_data.email
        )
        db.add(business_record)
        db.commit()
        
        logging.info(f"Owner account created successfully: {db_owner.name} (ID: {db_owner.emp_id}, Business ID: {db_owner.business_id})")
        
        # Send registration email
        user_id = f"USR{db_owner.emp_id}"
        email_sent = False
        try:
            logging.info(f"Attempting to send registration email to {owner_data.email}")
            email_sent = send_registration_email(
                to_email=owner_data.email,
                user_name=owner_data.name,
                user_id=user_id,
                role="owner",
                password=owner_data.password  # Send the password they just created
            )
            if email_sent:
                logging.info(f"✅ Registration email sent successfully to {owner_data.email}")
            else:
                logging.warning(f"⚠️ Registration email failed to send to {owner_data.email}")
        except Exception as e:
            logging.error(f"❌ Exception while sending registration email: {str(e)}", exc_info=True)
            # Don't fail registration if email fails
        
        return EmployeeSchema(
            emp_id=db_owner.emp_id,
            business_id=db_owner.business_id,
            name=db_owner.name,
            email=db_owner.email,
            phone_number=db_owner.phone_number,
            aadhar_number=db_owner.aadhar_number,
            address=db_owner.address,
            city=db_owner.city,
            state=db_owner.state,
            country=db_owner.country,
            role=db_owner.role,
            joining_date=db_owner.joining_date,
            custom_fields=db_owner.custom_fields
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error creating owner account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the owner account. Please try again."
        )


@router.post("/register", response_model=EmployeeSchema, status_code=status.HTTP_201_CREATED)
async def register_employee(
    employee: EmployeeCreate, 
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(require_role(["owner", "admin"]))
):
    """Register a new employee - requires owner or admin role"""
    try:
        # Check if email already exists
        existing_employee = db.query(Employee).filter(Employee.email == employee.email).first()
        if existing_employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already registered. Please use a different email."
            )
        
        # Hash password
        try:
            logging.info(f"Attempting to hash password for employee {employee.name}")
            hashed_password = pwd_context.hash(employee.password)
            logging.info(f"Successfully hashed password for employee {employee.name}")
        except Exception as e:
            logging.error(f"Error hashing password: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing password: {str(e)}"
            )
        
        # Create new employee (emp_id auto-generated by PostgreSQL sequence starting from 1000)
        db_employee = Employee(
            name=employee.name,
            email=employee.email,
            phone_number=employee.phone_number,
            aadhar_number=employee.aadhar_number,
            address=employee.address,
            city=employee.city,
            state=employee.state,
            country=employee.country,
            role=employee.role,
            joining_date=employee.joining_date,
            custom_fields=employee.custom_fields,
            hashed_password=hashed_password
        )
        
        db.add(db_employee)
        db.commit()
        db.refresh(db_employee)
        
        # Create a Business record with the business_id
        business_record = Business(
            business_id=str(db_employee.business_id),
            business_name="",
            owner_name="",
            phone_number="",
            email=""
        )
        db.add(business_record)
        db.commit()
        
        return EmployeeSchema(
            emp_id=db_employee.emp_id,
            name=db_employee.name,
            email=db_employee.email,
            phone_number=db_employee.phone_number,
            aadhar_number=db_employee.aadhar_number,
            address=db_employee.address,
            city=db_employee.city,
            state=db_employee.state,
            country=db_employee.country,
            role=db_employee.role,
            joining_date=db_employee.joining_date,
            custom_fields=db_employee.custom_fields
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/", response_model=EmployeeSchema, status_code=status.HTTP_201_CREATED)
async def create_employee(
    employee: EmployeeCreate, 
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """Create a new employee - requires owner, admin, or manager role"""
    try:
        # Check if email already exists
        db_employee = db.query(Employee).filter(Employee.email == employee.email).first()
        if db_employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password
        try:
            logging.info(f"Attempting to hash password for employee {employee.name}")
            hashed_password = pwd_context.hash(employee.password)
            logging.info(f"Successfully hashed password for employee {employee.name}")
        except Exception as e:
            logging.error(f"Error hashing password: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing password: {str(e)}"
            )
        
        # Create new employee with the same business_id as the current user (owner/admin)
        db_employee = Employee(
            name=employee.name,
            email=employee.email,
            phone_number=employee.phone_number,
            aadhar_number=employee.aadhar_number,
            address=employee.address,
            city=employee.city,
            state=employee.state,
            country=employee.country,
            role=employee.role,
            joining_date=employee.joining_date,
            custom_fields=employee.custom_fields,
            hashed_password=hashed_password,
            business_id=current_employee.business_id,  # Use the same business_id as the creator
            created_by=current_employee.emp_id
        )
        
        db.add(db_employee)
        db.commit()
        db.refresh(db_employee)
        
        # No need to create a Business record - employee shares the owner's business
        # Business record already exists from owner registration
        
        # Send registration email
        user_id = f"USR{db_employee.emp_id}"
        try:
            send_registration_email(
                to_email=employee.email,
                user_name=employee.name,
                user_id=user_id,
                role=employee.role,
                password=employee.password  # Send the password
            )
            logging.info(f"Registration email sent to {employee.email}")
        except Exception as e:
            logging.error(f"Failed to send registration email: {str(e)}")
            # Don't fail registration if email fails
        
        return EmployeeSchema(
            emp_id=db_employee.emp_id,
            business_id=db_employee.business_id,
            name=db_employee.name,
            email=db_employee.email,
            phone_number=db_employee.phone_number,
            aadhar_number=db_employee.aadhar_number,
            address=db_employee.address,
            city=db_employee.city,
            state=db_employee.state,
            country=db_employee.country,
            role=db_employee.role,
            joining_date=db_employee.joining_date,
            custom_fields=db_employee.custom_fields
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/", response_model=EmployeePaginatedResponse)
def get_employees(
    skip: int = 0, 
    limit: int = 100,
    filter_field: str = None,
    filter_value: str = None,
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """Get all employees with pagination and filtering - requires owner, admin, or manager role"""
    # Start with base query - filter by current employee's business_id
    query = db.query(Employee).filter(Employee.business_id == current_employee.business_id)
    
    # Apply filters if provided
    if filter_field and filter_value:
        filter_value_lower = filter_value.lower()
        
        # Handle custom fields filtering
        if filter_field.startswith("custom_"):
            custom_field_name = filter_field.replace("custom_", "")
            # Filter employees with custom fields that match
            # We need to check if any element in the JSON array has the key and contains the value
            from sqlalchemy import cast, String, func
            
            # Get all employees and filter in Python (more reliable for JSON filtering)
            all_employees = query.all()
            matching_ids = []
            
            for emp in all_employees:
                if emp.custom_fields:
                    for field_obj in emp.custom_fields:
                        if custom_field_name in field_obj:
                            field_value = str(field_obj[custom_field_name]).lower()
                            if filter_value_lower in field_value:
                                matching_ids.append(emp.emp_id)
                                break
            
            if matching_ids:
                query = query.filter(Employee.emp_id.in_(matching_ids))
            else:
                # No matches found, return empty result
                query = query.filter(Employee.emp_id == -1)
        else:
            # Regular field filtering
            if filter_field == "emp_id":
                # Exact match for emp_id
                if filter_value.isdigit():
                    query = query.filter(Employee.emp_id == int(filter_value))
            elif filter_field == "name":
                query = query.filter(Employee.name.ilike(f"%{filter_value}%"))
            elif filter_field == "email":
                query = query.filter(Employee.email.ilike(f"%{filter_value}%"))
            elif filter_field == "phone_number":
                query = query.filter(Employee.phone_number.ilike(f"%{filter_value}%"))
            elif filter_field == "aadhar_number":
                query = query.filter(Employee.aadhar_number.ilike(f"%{filter_value}%"))
            elif filter_field == "city":
                query = query.filter(Employee.city.ilike(f"%{filter_value}%"))
            elif filter_field == "state":
                query = query.filter(Employee.state.ilike(f"%{filter_value}%"))
            elif filter_field == "country":
                query = query.filter(Employee.country.ilike(f"%{filter_value}%"))
            elif filter_field == "role":
                query = query.filter(Employee.role.ilike(f"%{filter_value}%"))
    
    # Get total count after filtering
    total = query.count()
    
    # Get paginated employees
    employees = query.offset(skip).limit(limit).all()
    
    # Calculate page number (0-indexed)
    page = skip // limit if limit > 0 else 0
    
    return EmployeePaginatedResponse(
        items=employees,
        total=total,
        page=page,
        page_size=limit
    )


@router.get("/custom-fields/labels", response_model=List[str])
def get_custom_field_labels(
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """Get all unique custom field label names - requires owner, admin, or manager role"""
    employees = db.query(Employee).filter(Employee.business_id == current_employee.business_id).all()
    custom_labels = set()
    
    for employee in employees:
        if employee.custom_fields:
            for field_obj in employee.custom_fields:
                custom_labels.update(field_obj.keys())
    
    return sorted(list(custom_labels))


@router.get("/{emp_id}", response_model=EmployeeSchema)
def get_employee(
    emp_id: int, 
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """Get a specific employee - requires owner, admin, or manager role"""
    db_employee = db.query(Employee).filter(
        Employee.emp_id == emp_id,
        Employee.business_id == current_employee.business_id
    ).first()
    if db_employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return db_employee


@router.put("/{emp_id}", response_model=EmployeeSchema)
def update_employee(
    emp_id: int,
    employee_update: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(get_current_employee)
):
    """Update an employee - owner/admin/manager can update any, others can update self"""
    db_employee = db.query(Employee).filter(
        Employee.emp_id == emp_id,
        Employee.business_id == current_employee.business_id
    ).first()
    if db_employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Check if employee is updating themselves or if they have elevated privileges
    if current_employee.emp_id != emp_id and current_employee.role not in ["owner", "admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile"
        )
    
    # Check if email is being changed and if it's already taken
    if employee_update.email and employee_update.email != db_employee.email:
        email_exists = db.query(Employee).filter(Employee.email == employee_update.email).first()
        if email_exists:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Update employee fields
    update_data = employee_update.model_dump(exclude_unset=True)
    
    # Handle password separately if provided
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = pwd_context.hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(db_employee, field, value)
    
    db.commit()
    db.refresh(db_employee)
    return db_employee


@router.delete("/{emp_id}", status_code=status.HTTP_200_OK)
def delete_employee(
    emp_id: int, 
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(require_role(["owner", "admin"]))
):
    """Delete an employee - requires owner or admin role"""
    db_employee = db.query(Employee).filter(
        Employee.emp_id == emp_id,
        Employee.business_id == current_employee.business_id
    ).first()
    if db_employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    db.delete(db_employee)
    db.commit()
    return {"emp_id": emp_id, "detail": "deleted successfully"}


@router.post("/auth", response_model=TokenWithRefresh)
async def authenticate_employee(employee_details: EmployeeLogin, db: Session = Depends(get_db)):
    """Login endpoint for employees"""
    try:
        # Parse emp_id from user_id format (USR1000 -> 1000)
        user_id_str = employee_details.user_id.strip().upper()
        if not user_id_str.startswith("USR"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format. Use format: USR1000"
            )
        
        try:
            emp_id = int(user_id_str.replace("USR", ""))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format. Use format: USR1000"
            )
        
        logging.info(f"Authenticating employee with user ID: {user_id_str} (emp_id: {emp_id})")
        db_employee = db.query(Employee).filter(Employee.emp_id == emp_id).first()
        
        if not db_employee:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found. Please check your User ID."
            )
        
        if not verify_password(employee_details.password, db_employee.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password. Please try again."
            )

        # Create JWT access token and refresh token
        access_token = create_access_token({"sub": str(db_employee.emp_id), "role": db_employee.role})
        refresh_token = create_refresh_token({"sub": str(db_employee.emp_id), "role": db_employee.role})
        return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error during authentication: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )


@router.post("/refresh", response_model=TokenWithRefresh)
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token using refresh token"""
    # Validate refresh token
    if not is_refresh_token(request.refresh_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    payload = decode_token(request.refresh_token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    emp_id = payload.get("sub")
    role = payload.get("role")

    access_token = create_access_token({"sub": str(emp_id), "role": role})
    new_refresh = create_refresh_token({"sub": str(emp_id), "role": role})
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": new_refresh}


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Send password reset email
    Requires user_id and email for security
    """
    try:
        # Parse user_id to get emp_id
        if not request.user_id.startswith("USR"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )
        
        emp_id_str = request.user_id[3:]
        try:
            emp_id = int(emp_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )
        
        # Find employee by emp_id and email
        employee = db.query(Employee).filter(
            Employee.emp_id == emp_id,
            Employee.email == request.email
        ).first()
        
        if not employee:
            # Don't reveal if user exists for security
            return {"message": "If the user ID and email match, a password reset link will be sent."}
        
        # Create password reset token (valid for 1 hour)
        from datetime import timedelta
        reset_token = create_access_token(
            {"sub": str(employee.emp_id), "type": "password_reset"},
            expires_delta=timedelta(minutes=60)
        )
        
        # Send password reset email
        try:
            send_password_reset_email(
                to_email=employee.email,
                user_name=employee.name,
                reset_token=reset_token,
                user_id=request.user_id
            )
            logging.info(f"Password reset email sent to {employee.email}")
        except Exception as e:
            logging.error(f"Failed to send password reset email: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send password reset email. Please try again later."
            )
        
        return {"message": "If the user ID and email match, a password reset link will be sent."}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in forgot password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred processing your request"
        )


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset password using token from email
    """
    try:
        # Validate passwords match
        if request.new_password != request.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match"
            )
        
        # Validate token
        payload = decode_token(request.token)
        if not payload or payload.get("type") != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired reset token"
            )
        
        emp_id = int(payload.get("sub"))
        
        # Parse user_id to verify it matches token
        if not request.user_id.startswith("USR"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )
        
        request_emp_id = int(request.user_id[3:])
        if emp_id != request_emp_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID does not match reset token"
            )
        
        # Get employee
        employee = db.query(Employee).filter(Employee.emp_id == emp_id).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        
        # Hash new password
        hashed_password = pwd_context.hash(request.new_password)
        
        # Update password
        employee.hashed_password = hashed_password
        db.commit()
        
        logging.info(f"Password reset successful for employee {employee.name} (ID: {employee.emp_id})")
        
        return {"message": "Password reset successful. You can now login with your new password."}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error in reset password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred resetting your password"
        )


@router.post("/forgot-username-otp")
async def forgot_username_otp(request: ForgotUsernameRequest, db: Session = Depends(get_db)):
    """
    Send OTP to email for username recovery
    """
    try:
        # Find employee by email
        employee = db.query(Employee).filter(Employee.email == request.email).first()
        
        if not employee:
            # Don't reveal if email exists for security
            return {"message": "If the email is registered, an OTP will be sent."}
        
        # Generate and store OTP
        otp = store_otp(
            email=request.email,
            user_id=f"USR{employee.emp_id}",
            purpose="forgot_username"
        )
        
        # Send OTP email
        try:
            send_otp_email(
                to_email=employee.email,
                user_name=employee.name,
                otp=otp,
                purpose="recover your username"
            )
            logging.info(f"Username recovery OTP sent to {employee.email}")
        except Exception as e:
            logging.error(f"Failed to send OTP email: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP email. Please try again later."
            )
        
        return {"message": "If the email is registered, an OTP will be sent."}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in forgot username OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred processing your request"
        )


@router.post("/forgot-password-otp")
async def forgot_password_otp(request: ForgotPasswordOTPRequest, db: Session = Depends(get_db)):
    """
    Send OTP to email for password recovery
    """
    try:
        # Find employee by email
        employee = db.query(Employee).filter(Employee.email == request.email).first()
        
        if not employee:
            # Don't reveal if email exists for security
            return {"message": "If the email is registered, an OTP will be sent."}
        
        # Generate and store OTP
        otp = store_otp(
            email=request.email,
            user_id=f"USR{employee.emp_id}",
            purpose="forgot_password"
        )
        
        # Send OTP email
        try:
            send_otp_email(
                to_email=employee.email,
                user_name=employee.name,
                otp=otp,
                purpose="reset your password"
            )
            logging.info(f"Password recovery OTP sent to {employee.email}")
        except Exception as e:
            logging.error(f"Failed to send OTP email: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP email. Please try again later."
            )
        
        return {"message": "If the email is registered, an OTP will be sent."}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in forgot password OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred processing your request"
        )


@router.post("/verify-otp-username")
async def verify_otp_username(request: VerifyOTPRequest, db: Session = Depends(get_db)):
    """
    Verify OTP and send username to email
    """
    try:
        # Verify OTP
        user_id = verify_otp(
            email=request.email,
            otp=request.otp,
            purpose="forgot_username"
        )
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP"
            )
        
        # Get employee details
        emp_id = int(user_id[3:])  # Remove "USR" prefix
        employee = db.query(Employee).filter(Employee.emp_id == emp_id).first()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        
        # Send credentials email (username only)
        try:
            send_credentials_email(
                to_email=employee.email,
                user_name=employee.name,
                user_id=user_id,
                new_password=None  # No password for username recovery
            )
            logging.info(f"Username sent to {employee.email}")
        except Exception as e:
            logging.error(f"Failed to send credentials email: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send credentials email. Please try again later."
            )
        
        return {"message": "OTP verified successfully. Your username has been sent to your email."}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in verify OTP username: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred processing your request"
        )


@router.post("/verify-otp-password")
async def verify_otp_password(request: VerifyOTPRequest, db: Session = Depends(get_db)):
    """
    Verify OTP and send temporary password to email
    """
    try:
        # Verify OTP
        user_id = verify_otp(
            email=request.email,
            otp=request.otp,
            purpose="forgot_password"
        )
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP"
            )
        
        # Get employee details
        emp_id = int(user_id[3:])  # Remove "USR" prefix
        employee = db.query(Employee).filter(Employee.emp_id == emp_id).first()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        
        # Generate temporary password
        import secrets
        import string
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        # Hash and update password
        hashed_password = pwd_context.hash(temp_password)
        employee.hashed_password = hashed_password
        db.commit()
        
        # Send credentials email with temporary password
        try:
            send_credentials_email(
                to_email=employee.email,
                user_name=employee.name,
                user_id=user_id,
                new_password=temp_password
            )
            logging.info(f"Temporary password sent to {employee.email}")
        except Exception as e:
            db.rollback()
            logging.error(f"Failed to send credentials email: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send credentials email. Please try again later."
            )
        
        return {"message": "OTP verified successfully. A temporary password has been sent to your email."}
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error in verify OTP password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred processing your request"
        )


