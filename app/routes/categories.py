import logging
from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, DatabaseError, OperationalError

from app.database import get_db
from app.models.categories import Category
from app.models.employees import Employee
from app.schemas.categories import CategoryCreate, CategoryResponse, CategoryUpdate
from app.core.dependencies import get_current_employee, require_role

router = APIRouter(tags=["categories"])
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_exception_to_error_detail(e: Exception) -> dict:
    """Parse exception into structured error detail dictionary"""
    if isinstance(e, IntegrityError):
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        if "unique constraint" in error_msg.lower() or "duplicate key" in error_msg.lower():
            return {
                "error": "DuplicateEntryError",
                "message": "A category with this name already exists",
                "field": "name",
                "type": "duplicate_constraint",
                "suggestion": "Please use a different category name"
            }
        elif "not null" in error_msg.lower():
            return {
                "error": "MissingRequiredFieldError",
                "message": "Required fields are missing",
                "type": "missing_field",
                "suggestion": "Please ensure all required fields are provided"
            }
        
    elif isinstance(e, OperationalError):
        return {
            "error": "DatabaseConnectionError",
            "message": "Unable to connect to the database",
            "type": "database_connection",
            "suggestion": "Please try again later"
        }
    
    elif isinstance(e, DatabaseError):
        return {
            "error": "DatabaseError",
            "message": "A database error occurred",
            "type": "database_error",
            "suggestion": "Please verify your data and try again"
        }
    
    return {
        "error": "UnexpectedError",
        "message": "An unexpected error occurred",
        "type": "internal_error",
        "suggestion": "Please try again or contact support"
    }


@router.get(
    "",
    response_model=List[CategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all categories",
    description="Retrieve all product categories from database"
)
async def get_all_categories(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_employee)
):
    """
    Get all categories with proper error handling.
    Requires authentication.
    
    Returns:
        List[CategoryResponse]: List of all categories
    """
    try:
        logger.info("Fetching all categories")
        categories = db.query(Category).all()
        
        if not categories:
            logger.info("No categories found in database")
            return []
        
        logger.info(f"Successfully retrieved {len(categories)} categories")
        return categories
    
    except OperationalError as e:
        logger.error(f"Database connection error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=parse_exception_to_error_detail(e)
        )
    except DatabaseError as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=parse_exception_to_error_detail(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=parse_exception_to_error_detail(e)
        )


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get category by ID",
    description="Retrieve a specific category by its ID"
)
async def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_employee)
):
    """
    Get a specific category by ID.
    Requires authentication.
    
    Args:
        category_id: The ID of the category to retrieve
    
    Returns:
        CategoryResponse: The category data
    
    Raises:
        HTTPException: If category not found
    """
    try:
        logger.info(f"Fetching category with ID: {category_id}")
        category = db.query(Category).filter(Category.id == category_id).first()
        
        if not category:
            logger.warning(f"Category with ID {category_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "NotFoundError",
                    "message": f"Category with ID {category_id} not found",
                    "type": "resource_not_found"
                }
            )
        
        logger.info(f"Successfully retrieved category: {category.name}")
        return category
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=parse_exception_to_error_detail(e)
        )


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new category",
    description="Create a new product category"
)
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """
    Create a new category with validation and error handling.
    Requires owner, admin, or manager role.
    
    Args:
        category_data: Category creation data
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        CategoryResponse: The created category
    
    Raises:
        HTTPException: If category already exists or validation fails
    """
    try:
        logger.info(f"Creating new category: {category_data.name}")
        
        # Check if category already exists
        existing_category = db.query(Category).filter(
            Category.name.ilike(category_data.name)
        ).first()
        
        if existing_category:
            logger.warning(f"Category already exists: {category_data.name}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "DuplicateEntryError",
                    "message": "A category with this name already exists",
                    "field": "name",
                    "type": "duplicate_constraint",
                    "suggestion": "Please use a different category name"
                }
            )
        
        # Create new category
        new_category = Category(
            name=category_data.name.strip(),
            description=category_data.description.strip() if category_data.description else None
        )
        
        db.add(new_category)
        db.commit()
        db.refresh(new_category)
        
        logger.info(f"Successfully created category: {new_category.name} (ID: {new_category.id})")
        return new_category
    
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error creating category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=parse_exception_to_error_detail(e)
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=parse_exception_to_error_detail(e)
        )


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update category",
    description="Update an existing category"
)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """
    Update a category with validation and error handling.
    Requires owner, admin, or manager role.
    
    Args:
        category_id: The ID of the category to update
        category_data: Updated category data
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        CategoryResponse: The updated category
    
    Raises:
        HTTPException: If category not found or validation fails
    """
    try:
        logger.info(f"Updating category with ID: {category_id}")
        
        category = db.query(Category).filter(Category.id == category_id).first()
        
        if not category:
            logger.warning(f"Category with ID {category_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "NotFoundError",
                    "message": f"Category with ID {category_id} not found",
                    "type": "resource_not_found"
                }
            )
        
        # Check for duplicate name if being updated
        if category_data.name and category_data.name != category.name:
            existing = db.query(Category).filter(
                Category.name.ilike(category_data.name)
            ).first()
            if existing:
                logger.warning(f"Category name already exists: {category_data.name}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "DuplicateEntryError",
                        "message": "A category with this name already exists",
                        "field": "name",
                        "type": "duplicate_constraint"
                    }
                )
        
        # Update fields
        if category_data.name:
            category.name = category_data.name.strip()
        if category_data.description is not None:
            category.description = category_data.description.strip() if category_data.description else None
        
        db.commit()
        db.refresh(category)
        
        logger.info(f"Successfully updated category: {category.name} (ID: {category.id})")
        return category
    
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error updating category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=parse_exception_to_error_detail(e)
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error updating category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=parse_exception_to_error_detail(e)
        )


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete category",
    description="Delete a category by ID"
)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role(["owner", "admin"]))
):
    """
    Delete a category with proper error handling.
    Requires owner or admin role.
    
    Args:
        category_id: The ID of the category to delete
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        dict: Success message
    
    Raises:
        HTTPException: If category not found
    """
    try:
        logger.info(f"Deleting category with ID: {category_id}")
        
        category = db.query(Category).filter(Category.id == category_id).first()
        
        if not category:
            logger.warning(f"Category with ID {category_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "NotFoundError",
                    "message": f"Category with ID {category_id} not found",
                    "type": "resource_not_found"
                }
            )
        
        db.delete(category)
        db.commit()
        
        logger.info(f"Successfully deleted category with ID: {category_id}")
        return {
            "message": f"Category '{category.name}' deleted successfully",
            "id": category_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error deleting category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=parse_exception_to_error_detail(e)
        )
