from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging
from app.database import get_db
from app.models.employees import Employee
from app.models.employee_labels import EmployeeLabel
from app.models.business import Business
from app.models.stores import Store
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
    ForgotPasswordOTPRequest,
    ChangePasswordRequest
)
from app.core.security import create_access_token, create_refresh_token, decode_token, is_refresh_token
from app.core.dependencies import get_current_employee, require_role
from passlib.context import CryptContext
from app.utils.email_service import send_registration_email, send_password_reset_email, send_otp_email, send_credentials_email
from app.utils.otp_service import store_otp, verify_otp
from fastapi import UploadFile, File
from app.services.storage_service import storage_service
import os
import shutil
from pathlib import Path

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
        # Note: Same email can now register multiple businesses (owner in Business A, owner in Business B)
        # No email uniqueness check needed - composite constraint (email, business_id) allows this
        
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
                business_id=db_owner.business_id,
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
        # Check if email already exists in the SAME business
        existing_employee = db.query(Employee).filter(
            Employee.email == employee.email,
            Employee.business_id == current_employee.business_id
        ).first()
        if existing_employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email is already registered in your business. Please use a different email."
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
        # Note: Same email can be used multiple times within a business
        # Database has no unique constraint on email anymore
        
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
            custom_fields=None,  # Don't store in JSON, use employee_labels table
            hashed_password=hashed_password,
            business_id=current_employee.business_id,  # Use the same business_id as the creator
            store_id=employee.store_id,  # Store assignment
            created_by=current_employee.emp_id
        )
        
        db.add(db_employee)
        db.commit()
        db.refresh(db_employee)
        
        # Save custom labels to employee_labels table
        logging.info(f"Custom fields data received: {employee.custom_fields}")
        if employee.custom_fields:
            logging.info(f"Saving {len(employee.custom_fields)} custom field(s) to employee_labels table")
            for field_obj in employee.custom_fields:
                for label_name, label_value in field_obj.items():
                    logging.info(f"Saving label: {label_name} = {label_value}")
                    label = EmployeeLabel(
                        emp_id=db_employee.emp_id,
                        business_id=db_employee.business_id,
                        label_name=label_name,
                        label_value=label_value
                    )
                    db.add(label)
            db.commit()
            logging.info(f"Successfully saved custom fields to employee_labels table")
        else:
            logging.info("No custom fields to save")
        
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
                business_id=db_employee.business_id,
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
    filters: str = None,
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """Get all employees with pagination and filtering - requires owner, admin, or manager role"""
    import json
    
    # Start with base query - filter by current employee's business_id
    query = db.query(Employee).filter(Employee.business_id == current_employee.business_id)
    
    # Parse multiple filters if provided (new feature)
    filter_list = []
    if filters:
        try:
            filter_list = json.loads(filters)
        except:
            pass
    
    # Track if we need to join Store table for store filtering
    store_joined = False
    
    # Apply multiple filters
    if filter_list:
        for filter_item in filter_list:
            filter_field_item = filter_item.get('field')
            filter_value_item = filter_item.get('value')
            
            if not filter_field_item or not filter_value_item:
                continue
                
            filter_value_lower = filter_value_item.lower()
            
            # Handle custom fields filtering using employee_labels table
            if filter_field_item.startswith("custom_"):
                custom_field_name = filter_field_item.replace("custom_", "")
                # Query employee_labels table for matching labels
                matching_labels = db.query(EmployeeLabel.emp_id).filter(
                    EmployeeLabel.business_id == current_employee.business_id,
                    EmployeeLabel.label_name == custom_field_name,
                    EmployeeLabel.label_value.ilike(f"%{filter_value_item}%")
                ).distinct().all()
                
                matching_ids = [label.emp_id for label in matching_labels]
                
                if matching_ids:
                    query = query.filter(Employee.emp_id.in_(matching_ids))
                else:
                    # No matches found, return empty result
                    query = query.filter(Employee.emp_id == -1)
            else:
                # Regular field filtering
                if filter_field_item == "emp_id":
                    # Exact match for emp_id
                    if filter_value_item.isdigit():
                        query = query.filter(Employee.emp_id == int(filter_value_item))
                elif filter_field_item == "name":
                    query = query.filter(Employee.name.ilike(f"%{filter_value_item}%"))
                elif filter_field_item == "email":
                    query = query.filter(Employee.email.ilike(f"%{filter_value_item}%"))
                elif filter_field_item == "phone_number":
                    query = query.filter(Employee.phone_number.ilike(f"%{filter_value_item}%"))
                elif filter_field_item == "aadhar_number":
                    query = query.filter(Employee.aadhar_number.ilike(f"%{filter_value_item}%"))
                elif filter_field_item == "city":
                    query = query.filter(Employee.city.ilike(f"%{filter_value_item}%"))
                elif filter_field_item == "state":
                    query = query.filter(Employee.state.ilike(f"%{filter_value_item}%"))
                elif filter_field_item == "country":
                    query = query.filter(Employee.country.ilike(f"%{filter_value_item}%"))
                elif filter_field_item == "role":
                    query = query.filter(Employee.role.ilike(f"%{filter_value_item}%"))
                elif filter_field_item == "store_id":
                    # Filter by store name using subquery to avoid join conflicts
                    if not store_joined:
                        query = query.join(Store, Employee.store_id == Store.id, isouter=True)
                        store_joined = True
                    query = query.filter(Store.store_name.ilike(f"%{filter_value_item}%"))
    # Legacy single filter support (for backward compatibility)
    elif filter_field and filter_value:
        filter_value_lower = filter_value.lower()
        
        # Handle custom fields filtering using employee_labels table
        if filter_field.startswith("custom_"):
            custom_field_name = filter_field.replace("custom_", "")
            # Query employee_labels table for matching labels
            matching_labels = db.query(EmployeeLabel.emp_id).filter(
                EmployeeLabel.business_id == current_employee.business_id,
                EmployeeLabel.label_name == custom_field_name,
                EmployeeLabel.label_value.ilike(f"%{filter_value}%")
            ).distinct().all()
            
            matching_ids = [label.emp_id for label in matching_labels]
            
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
            elif filter_field == "store_id":
                # Filter by store name - join with Store table
                query = query.join(Store, Employee.store_id == Store.id, isouter=True).filter(
                    Store.store_name.ilike(f"%{filter_value}%")
                )
    
    # Get total count after filtering
    total = query.count()
    
    # Get paginated employees
    employees = query.offset(skip).limit(limit).all()
    
    # PERFORMANCE OPTIMIZATION: Fetch all stores and labels in bulk
    import base64
    
    # Get all employee IDs
    emp_ids = [emp.emp_id for emp in employees]
    
    # Initialize dicts
    stores_dict = {}
    labels_by_emp = {}
    
    # Only fetch if there are employees
    if emp_ids:
        # Bulk fetch all stores for these employees
        store_ids = list(set([emp.store_id for emp in employees if emp.store_id]))
        if store_ids:
            stores = db.query(Store).filter(Store.id.in_(store_ids)).all()
            stores_dict = {store.id: store for store in stores}
        
        # Bulk fetch all labels for these employees  
        labels_query = db.query(EmployeeLabel).filter(
            EmployeeLabel.emp_id.in_(emp_ids),
            EmployeeLabel.business_id == current_employee.business_id
        ).all()
        
        # Group labels by emp_id
        for label in labels_query:
            if label.emp_id not in labels_by_emp:
                labels_by_emp[label.emp_id] = []
            labels_by_emp[label.emp_id].append({label.label_name: label.label_value})
    
    # Build response list
    employee_list = []
    for emp in employees:
        # Get store details from dict (no query)
        store_id_display = None
        store_name = None
        if emp.store_id and emp.store_id in stores_dict:
            store = stores_dict[emp.store_id]
            store_id_display = f"STR{store.store_sequence}"
            store_name = store.store_name
        
        # Get custom fields from dict (no query)
        custom_fields = labels_by_emp.get(emp.emp_id, [])
        
        # Avatars are now stored as URLs in GCS
        avatar_url = emp.avatar_url
        thumbnail_url = emp.thumbnail_url
        
        emp_dict = {
            "emp_id": emp.emp_id,
            "business_id": emp.business_id,
            "business_id_display": f"BUS{emp.business_id}",
            "user_id": f"USR{emp.emp_id}",
            "name": emp.name,
            "email": emp.email,
            "phone_number": emp.phone_number,
            "aadhar_number": emp.aadhar_number,
            "address": emp.address,
            "city": emp.city,
            "state": emp.state,
            "country": emp.country,
            "role": emp.role,
            "joining_date": emp.joining_date,
            "custom_fields": custom_fields if custom_fields else None,
            "store_id": emp.store_id,
            "store_id_display": store_id_display,
            "store_name": store_name,
            "created_by": emp.created_by,
            "updated_by": emp.updated_by,
            "avatar_url": avatar_url,
            "thumbnail_url": thumbnail_url
        }
        employee_list.append(emp_dict)
    
    # Calculate page number (0-indexed)
    page = skip // limit if limit > 0 else 0
    
    return EmployeePaginatedResponse(
        items=employee_list,
        total=total,
        page=page,
        page_size=limit
    )


@router.get("/custom-fields/labels", response_model=List[str])
def get_custom_field_labels(
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """Get all unique custom field label names from employee_labels table"""
    labels = db.query(EmployeeLabel.label_name).filter(
        EmployeeLabel.business_id == current_employee.business_id
    ).distinct().all()
    
    return sorted([label[0] for label in labels])


@router.get("/custom-fields/values/{label_name}", response_model=List[str])
def get_label_values(
    label_name: str,
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """
    Get all unique values for a specific label name.
    Returns values from both template (label_values array) and employee records (label_value).
    """
    # Get template values (stored as array in label_values column where emp_id is NULL)
    template_record = db.query(EmployeeLabel).filter(
        EmployeeLabel.business_id == current_employee.business_id,
        EmployeeLabel.label_name == label_name,
        EmployeeLabel.emp_id == None
    ).first()
    
    template_values = template_record.label_values if template_record and template_record.label_values else []
    
    # Get values from actual employee records (label_value column where emp_id is NOT NULL)
    employee_values = db.query(EmployeeLabel.label_value).filter(
        EmployeeLabel.business_id == current_employee.business_id,
        EmployeeLabel.label_name == label_name,
        EmployeeLabel.emp_id != None,
        EmployeeLabel.label_value != None
    ).distinct().all()
    
    employee_values = [value[0] for value in employee_values]
    
    # Combine and deduplicate
    all_values = list(set(template_values + employee_values))
    
    return sorted(all_values)


@router.post("/custom-fields/define-label", status_code=status.HTTP_201_CREATED)
def define_custom_label(
    label_data: dict,
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """
    Define a custom label with predefined values.
    Stores values as an array in a single row with emp_id=NULL (template record).
    
    Request body: {"label_name": "Size", "values": ["XL", "L", "M", "S"]}
    """
    label_name = label_data.get("label_name", "").strip()
    values = label_data.get("values", [])
    
    if not label_name:
        raise HTTPException(status_code=400, detail="label_name is required")
    
    if not values or not isinstance(values, list):
        raise HTTPException(status_code=400, detail="values must be a non-empty array")
    
    # Filter out empty values and deduplicate
    valid_values = list(set([v.strip() for v in values if isinstance(v, str) and v.strip()]))
    
    if not valid_values:
        raise HTTPException(status_code=400, detail="At least one valid value is required")
    
    try:
        # Check if template already exists for this label
        existing_template = db.query(EmployeeLabel).filter(
            EmployeeLabel.business_id == current_employee.business_id,
            EmployeeLabel.label_name == label_name,
            EmployeeLabel.emp_id == None
        ).first()
        
        if existing_template:
            # Merge new values with existing values
            current_values = existing_template.label_values or []
            merged_values = list(set(current_values + valid_values))
            existing_template.label_values = merged_values
            new_count = len(merged_values) - len(current_values)
            
            db.commit()
            
            logging.info(f"Updated custom label '{label_name}' with {new_count} new value(s) for business {current_employee.business_id}")
            
            return {
                "message": f"Custom label '{label_name}' updated successfully",
                "label_name": label_name,
                "new_values_added": new_count,
                "total_values": len(merged_values)
            }
        else:
            # Create new template record with array of values
            template_label = EmployeeLabel(
                emp_id=None,  # NULL emp_id indicates this is a template
                business_id=current_employee.business_id,
                label_name=label_name,
                label_value=None,  # Not used for templates
                label_values=valid_values  # Store array of values
            )
            db.add(template_label)
            db.commit()
            
            logging.info(f"Created custom label '{label_name}' with {len(valid_values)} value(s) for business {current_employee.business_id}")
            
            return {
                "message": f"Custom label '{label_name}' created successfully",
                "label_name": label_name,
                "total_values": len(valid_values)
            }
        
    except Exception as e:
        db.rollback()
        logging.error(f"Error defining custom label: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save custom label: {str(e)}")


# Profile endpoints - Must be before /{emp_id} route
@router.get("/me", response_model=EmployeeSchema)
def get_current_employee_profile(
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Get current logged-in employee profile data"""
    logging.info(f"Getting profile for employee ID: {current_employee.emp_id}, Name: {current_employee.name}")
    
    # Get store details if employee has a store_id
    store_id_display = None
    store_name = None
    if current_employee.store_id:
        store = db.query(Store).filter(Store.id == current_employee.store_id).first()
        if store:
            store_id_display = f"STR{store.store_sequence}"
            store_name = store.store_name
    
    # Load custom fields from employee_labels table
    custom_fields = []
    labels = db.query(EmployeeLabel).filter(
        EmployeeLabel.emp_id == current_employee.emp_id,
        EmployeeLabel.business_id == current_employee.business_id
    ).all()
    for label in labels:
        custom_fields.append({label.label_name: label.label_value})
    
    logging.info(f"Employee profile retrieved for: {current_employee.name}")
    
    # Return formatted response with business_id_display
    return {
        "emp_id": current_employee.emp_id,
        "business_id": current_employee.business_id,
        "business_id_display": f"BUS{current_employee.business_id}",
        "user_id": f"USR{current_employee.emp_id}",
        "name": current_employee.name,
        "email": current_employee.email,
        "phone_number": current_employee.phone_number,
        "aadhar_number": current_employee.aadhar_number,
        "address": current_employee.address,
        "city": current_employee.city,
        "state": current_employee.state,
        "country": current_employee.country,
        "role": current_employee.role,
        "joining_date": current_employee.joining_date,
        "custom_fields": custom_fields if custom_fields else None,
        "store_id": current_employee.store_id,
        "store_id_display": store_id_display,
        "store_name": store_name,
        "created_by": current_employee.created_by,
        "updated_by": current_employee.updated_by,
        "avatar_url": current_employee.avatar_url,
        "thumbnail_url": current_employee.thumbnail_url
    }


@router.get("/me/password", status_code=status.HTTP_200_OK)
def get_current_employee_password(
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Get current employee's password (unhashed) - Security warning: Use with caution"""
    # Note: This is generally not recommended in production
    # Passwords should remain hashed. This is for demonstration purposes only.
    # In a real application, you would NOT expose passwords.
    
    # Since passwords are hashed, we cannot retrieve the original password
    # This endpoint returns a message indicating the password is encrypted
    return {
        "password": "••••••••",
        "message": "Password is encrypted and cannot be retrieved. Use change password instead.",
        "encrypted": True
    }


@router.post("/avatar/upload", status_code=status.HTTP_200_OK)
@router.post("/upload-avatar", status_code=status.HTTP_200_OK)
async def upload_avatar(
    avatar: UploadFile = File(...),
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Upload avatar for current employee to Google Cloud Storage"""
    # Validate file type
    if not avatar.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Validate file size (max 5MB)
    avatar.file.seek(0, 2)
    file_size = avatar.file.tell()
    avatar.file.seek(0)
    
    if file_size > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must not exceed 5MB"
        )
    
    try:
        # Delete old avatar if exists
        if current_employee.avatar_url:
            storage_service.delete_image(current_employee.avatar_url)
        
        # Upload new avatar with thumbnail
        result = await storage_service.upload_image(avatar, "avatars", create_thumbnail=True)
        
        # Update employee record
        current_employee.avatar_url = result["url"]
        current_employee.thumbnail_url = result.get("thumbnail_url")
        db.commit()
        db.refresh(current_employee)
        
        logging.info(f"Avatar uploaded successfully for employee {current_employee.emp_id}")
        
        return {
            "message": "Avatar uploaded successfully",
            "avatar_url": current_employee.avatar_url,
            "thumbnail_url": current_employee.thumbnail_url
        }
    except Exception as e:
        db.rollback()
        logging.error(f"Error uploading avatar: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload avatar: {str(e)}"
        )


@router.delete("/avatar", status_code=status.HTTP_200_OK)
async def delete_avatar(
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Delete avatar for current employee"""
    if not current_employee.avatar_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No avatar found"
        )
    
    try:
        # Delete from GCS
        storage_service.delete_image(current_employee.avatar_url)
        
        # Update employee record
        current_employee.avatar_url = None
        current_employee.thumbnail_url = None
        db.commit()
        
        return {"message": "Avatar deleted successfully"}
    except Exception as e:
        db.rollback()
        logging.error(f"Error deleting avatar: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete avatar: {str(e)}"
        )


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
    
    # Get store details if employee has a store_id
    store_id_display = None
    store_name = None
    if db_employee.store_id:
        store = db.query(Store).filter(Store.id == db_employee.store_id).first()
        if store:
            store_id_display = f"STR{store.store_sequence}"
            store_name = store.store_name
    
    # Load custom fields from employee_labels table
    custom_fields = []
    labels = db.query(EmployeeLabel).filter(
        EmployeeLabel.emp_id == db_employee.emp_id,
        EmployeeLabel.business_id == db_employee.business_id
    ).all()
    for label in labels:
        custom_fields.append({label.label_name: label.label_value})
    
    # Return formatted response with business_id_display
    return {
        "emp_id": db_employee.emp_id,
        "business_id": db_employee.business_id,
        "business_id_display": f"BUS{db_employee.business_id}",
        "user_id": f"USR{db_employee.emp_id}",
        "name": db_employee.name,
        "email": db_employee.email,
        "phone_number": db_employee.phone_number,
        "aadhar_number": db_employee.aadhar_number,
        "address": db_employee.address,
        "city": db_employee.city,
        "state": db_employee.state,
        "country": db_employee.country,
        "role": db_employee.role,
        "joining_date": db_employee.joining_date,
        "custom_fields": custom_fields if custom_fields else None,
        "store_id": db_employee.store_id,
        "store_id_display": store_id_display,
        "store_name": store_name,
        "created_by": db_employee.created_by,
        "updated_by": db_employee.updated_by,
        "avatar_url": db_employee.avatar_url,
        "thumbnail_url": db_employee.thumbnail_url
    }


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
    
    # Check if email is being changed and if it's already taken in the same business
    if employee_update.email and employee_update.email != db_employee.email:
        email_exists = db.query(Employee).filter(
            Employee.email == employee_update.email,
            Employee.business_id == current_employee.business_id
        ).first()
        if email_exists:
            raise HTTPException(status_code=400, detail="Email already registered in your business")
    
    # Update employee fields
    update_data = employee_update.model_dump(exclude_unset=True)
    
    # Handle password separately if provided
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = pwd_context.hash(update_data.pop("password"))
    
    # Handle custom_fields separately
    custom_fields_data = update_data.pop("custom_fields", None)
    
    for field, value in update_data.items():
        setattr(db_employee, field, value)
    
    db.commit()
    
    # Update custom labels in employee_labels table
    logging.info(f"Custom fields data received for update: {custom_fields_data}")
    if custom_fields_data is not None:
        # Delete existing labels for this employee
        deleted_count = db.query(EmployeeLabel).filter(
            EmployeeLabel.emp_id == emp_id
        ).delete()
        logging.info(f"Deleted {deleted_count} existing label(s) for employee {emp_id}")
        
        # Add new labels
        if custom_fields_data:
            logging.info(f"Saving {len(custom_fields_data)} custom field(s) to employee_labels table")
            for field_obj in custom_fields_data:
                for label_name, label_value in field_obj.items():
                    logging.info(f"Saving label: {label_name} = {label_value}")
                    label = EmployeeLabel(
                        emp_id=emp_id,
                        business_id=db_employee.business_id,
                        label_name=label_name,
                        label_value=label_value
                    )
                    db.add(label)
            logging.info(f"Successfully saved custom fields to employee_labels table")
        else:
            logging.info("No custom fields to save (custom_fields is empty)")
        db.commit()
    else:
        logging.info("Custom fields not included in update request")
    
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

    # Check if employee is an owner with associated business
    if db_employee.role == "owner":
        # Check if this owner has a business registered
        associated_business = db.query(Business).filter(
            Business.business_id == str(db_employee.business_id)
        ).first()
        
        if associated_business:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete owner with associated business. Business and its employees must be removed first."
            )

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
    Send all user IDs (usernames) associated with an email
    Since same email can exist in multiple businesses, returns all matches
    If business_id is provided, only returns User ID for that specific business
    """
    try:
        # Build query based on whether business_id is provided
        query = db.query(Employee).filter(Employee.email == request.email)
        
        # If business_id provided, filter by it
        if request.business_id:
            query = query.filter(Employee.business_id == request.business_id)
        
        employees = query.all()
        
        if not employees:
            # Don't reveal if email exists for security
            return {"message": "If the email is registered, your user IDs will be sent."}
        
        # Prepare list of user IDs with business info and store details
        from app.models.stores import Store
        user_ids = []
        for emp in employees:
            # Get store details if employee has a store_id
            store_id_display = None
            store_name = None
            if emp.store_id:
                store = db.query(Store).filter(Store.id == emp.store_id).first()
                if store:
                    store_id_display = f"STR{store.store_sequence}"
                    store_name = store.store_name
            
            user_ids.append({
                "user_id": f"USR{emp.emp_id}",
                "role": emp.role,
                "business_id": f"BUS{emp.business_id}",
                "store_id": store_id_display,
                "store_name": store_name
            })
        
        # Send email with all user IDs
        try:
            send_credentials_email(
                to_email=request.email,
                user_name=employees[0].name,  # Use first name (should be same person)
                user_ids=user_ids
            )
            logging.info(f"Username recovery sent to {request.email} with {len(user_ids)} user ID(s)")
        except Exception as e:
            logging.error(f"Failed to send credentials email: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send email. Please try again later."
            )
        
        return {"message": "If the email is registered, your user IDs will be sent."}
    
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
    Requires BOTH user_id and email since same email can exist in multiple businesses
    """
    try:
        # Parse user_id to get emp_id
        if not request.user_id or not request.user_id.startswith("USR"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format. Please provide user ID in format USR1000"
            )
        
        emp_id_str = request.user_id[3:]
        try:
            emp_id = int(emp_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )
        
        # Find employee by BOTH emp_id and email
        employee = db.query(Employee).filter(
            Employee.emp_id == emp_id,
            Employee.email == request.email
        ).first()
        
        if not employee:
            # Don't reveal if email/user_id combination exists for security
            return {"message": "If the user ID and email match, an OTP will be sent."}
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


@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    request: ChangePasswordRequest,
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Change password for current employee"""
    # Verify current password
    if not verify_password(request.current_password, current_employee.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters long"
        )
    
    # Hash and update password
    hashed_password = pwd_context.hash(request.new_password)
    current_employee.hashed_password = hashed_password
    db.commit()
    
    return {"message": "Password changed successfully"}




