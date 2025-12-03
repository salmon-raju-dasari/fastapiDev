import logging
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.business import Business
from app.models.employees import Employee
from app.schemas.business import BusinessCreate, BusinessResponse, BusinessUpdate
from app.core.dependencies import get_current_employee, require_role

router = APIRouter(tags=["business"])
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_business_id(db: Session) -> str:
    """Generate a unique business ID using UUID"""
    return str(uuid.uuid4())

@router.post("/", response_model=BusinessResponse, status_code=status.HTTP_201_CREATED)
async def create_business(
    business_data: BusinessCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role(["owner"]))
):
    """Create business details - only owner can create"""
    try:
        # Validate required fields
        if not business_data.business_name or not business_data.business_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Business name is required and cannot be empty."
            )
        
        if not business_data.owner_name or not business_data.owner_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Owner name is required and cannot be empty."
            )
        
        if not business_data.phone_number or not business_data.phone_number.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is required and cannot be empty."
            )
        
        if not business_data.email or not business_data.email.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required and cannot be empty."
            )
        
        # Check if business details already exist (only one business allowed)
        existing = db.query(Business).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Business details already exist. You can only have one business. Please update the existing business instead of creating a new one."
            )
        
        logger.info(f"Owner {current_user.name} ({current_user.email}) is creating business details")
        
        # Generate unique business_id
        business_id = generate_business_id(db)
        
        # Create business with generated business_id
        db_business = Business(**business_data.dict(), business_id=business_id)
        db.add(db_business)
        db.commit()
        db.refresh(db_business)
        
        logger.info(f"Business created successfully: {db_business.business_name} (ID: {business_id})")
        return db_business
    
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while creating business: {str(e)}")
        
        # Check for specific constraint violations
        error_msg = str(e.orig).lower()
        if "business_id" in error_msg and "unique" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Business ID conflict. Please try again."
            )
        elif "email" in error_msg and "unique" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A business with this email already exists."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid business data. Please check all fields and try again."
            )
    except ValueError as e:
        db.rollback()
        logger.error(f"Validation error while creating business: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data provided: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating business: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the business. Please try again or contact support if the problem persists."
        )

@router.get("/", response_model=BusinessResponse)
async def get_business(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_employee)
):
    """Get business details - all authenticated users can view"""
    try:
        business = db.query(Business).first()
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No business details found. Please create your business profile first to get started."
            )
        
        # Create response with has_logo indicator
        response_data = BusinessResponse.from_orm(business)
        response_data.has_logo = business.logo_data is not None
        return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching business: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while loading business details. Please refresh the page or contact support."
        )

@router.put("/", response_model=BusinessResponse)
async def update_business(
    business_data: BusinessUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role(["owner", "admin"]))
):
    """Update business details - owner and admin can update"""
    try:
        business = db.query(Business).first()
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No business found to update. Please create business details first."
            )
        
        logger.info(f"User {current_user.name} ({current_user.email}) is updating business details")
        
        # Update only provided fields
        update_data = business_data.dict(exclude_unset=True)
        
        # Validate that at least one field is provided
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update. Please provide at least one field to update."
            )
        
        # Validate specific fields if provided
        if 'business_name' in update_data and not update_data['business_name'].strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Business name cannot be empty."
            )
        
        if 'owner_name' in update_data and not update_data['owner_name'].strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Owner name cannot be empty."
            )
        
        if 'email' in update_data and not update_data['email'].strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email cannot be empty."
            )
        
        if 'phone_number' in update_data and not update_data['phone_number'].strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number cannot be empty."
            )
        
        for field, value in update_data.items():
            setattr(business, field, value)
        
        db.commit()
        db.refresh(business)
        
        logger.info(f"Business details updated successfully for: {business.business_name}")
        return business
    
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while updating business: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Update failed due to duplicate data. Please check your email and other unique fields."
        )
    except ValueError as e:
        db.rollback()
        logger.error(f"Validation error while updating business: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data provided: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error updating business: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating business details. Please try again or contact support."
        )

@router.post("/upload-logo")
async def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role(["owner", "admin"]))
):
    """Upload business logo - owner and admin can upload"""
    try:
        # Validate file is provided
        if not file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided. Please select an image file to upload."
            )
        
        # Validate file type
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type '{file.content_type}'. Only JPEG, PNG, GIF, and WebP images are allowed."
            )
        
        # Validate file size (max 5MB)
        file_content = await file.read()
        file_size_mb = len(file_content) / (1024 * 1024)
        
        if len(file_content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file provided. Please select a valid image file."
            )
        
        if len(file_content) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size ({file_size_mb:.2f} MB) exceeds the maximum limit of 5 MB. Please compress the image or choose a smaller file."
            )
        
        # Get business record
        business = db.query(Business).first()
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No business found. Please create business details before uploading a logo."
            )
        
        logger.info(f"User {current_user.name} is uploading logo for business: {business.business_name} (Size: {file_size_mb:.2f} MB)")
        
        # Save logo to database
        business.logo_data = file_content
        business.logo_content_type = file.content_type
        db.commit()
        
        logger.info(f"Logo uploaded successfully for business: {business.business_name}")
        return {"message": "Logo uploaded successfully", "file_size_mb": round(file_size_mb, 2)}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error uploading logo: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while uploading the logo. Please try again with a different image or contact support."
        )

@router.get("/logo")
async def get_logo(
    db: Session = Depends(get_db)
):
    """Get business logo - public access (no authentication required)"""
    try:
        business = db.query(Business).first()
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No business found."
            )
        
        if not business.logo_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No logo uploaded yet. Please upload a business logo first."
            )
        
        # Return logo as binary response with correct content type
        return Response(
            content=business.logo_data,
            media_type=business.logo_content_type or "image/jpeg"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching logo: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while loading the logo. Please try again."
        )
