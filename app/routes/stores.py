import logging
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.stores import Store
from app.models.business import Business
from app.models.employees import Employee
from app.schemas.stores import StoreCreate, StoreResponse, StoreUpdate
from app.core.dependencies import get_current_employee, require_role

router = APIRouter(tags=["stores"])
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_store_id() -> str:
    """Generate a unique store ID using UUID"""
    return str(uuid.uuid4())

@router.post("/", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
async def create_store(
    store_data: StoreCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role(["owner", "admin"]))
):
    """Create a new store - only owner and admin can create"""
    try:
        # Validate store name
        if not store_data.store_name or not store_data.store_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Store name is required and cannot be empty."
            )
        
        # Get business details
        business = db.query(Business).first()
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No business profile found. Please create a business profile before adding stores."
            )
        
        logger.info(f"User {current_user.name} is creating a new store: {store_data.store_name}")
        
        # Generate unique store_id
        store_id = generate_store_id()
        
        # Create store with generated store_id and business_id
        db_store = Store(
            **store_data.dict(),
            store_id=store_id,
            business_id=business.business_id
        )
        db.add(db_store)
        db.commit()
        db.refresh(db_store)
        
        logger.info(f"Store created successfully: {db_store.store_name} (ID: {store_id})")
        return db_store
    
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while creating store: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A store with this information already exists. Please use different details."
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating store: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the store. Please try again."
        )

@router.get("/", response_model=List[StoreResponse])
async def get_stores(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_employee)
):
    """Get all stores - all authenticated users can view"""
    try:
        stores = db.query(Store).all()
        return stores
    except Exception as e:
        logger.error(f"Error fetching stores: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while loading stores."
        )

@router.get("/{store_id}", response_model=StoreResponse)
async def get_store(
    store_id: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_employee)
):
    """Get a specific store by ID"""
    try:
        store = db.query(Store).filter(Store.store_id == store_id).first()
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store with ID {store_id} not found."
            )
        return store
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching store: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while loading the store."
        )

@router.put("/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: str,
    store_data: StoreUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role(["owner", "admin"]))
):
    """Update store details - owner and admin can update"""
    try:
        store = db.query(Store).filter(Store.store_id == store_id).first()
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store with ID {store_id} not found."
            )
        
        logger.info(f"User {current_user.name} is updating store: {store.store_name}")
        
        # Update only provided fields
        update_data = store_data.dict(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update."
            )
        
        # Validate store name if provided
        if 'store_name' in update_data and not update_data['store_name'].strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Store name cannot be empty."
            )
        
        for field, value in update_data.items():
            setattr(store, field, value)
        
        db.commit()
        db.refresh(store)
        
        logger.info(f"Store updated successfully: {store.store_name}")
        return store
    
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while updating store: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Update failed due to duplicate data."
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error updating store: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating the store."
        )

@router.delete("/{store_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_store(
    store_id: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role(["owner", "admin"]))
):
    """Delete a store - only owner and admin can delete"""
    try:
        store = db.query(Store).filter(Store.store_id == store_id).first()
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store with ID {store_id} not found."
            )
        
        logger.info(f"User {current_user.name} is deleting store: {store.store_name}")
        
        db.delete(store)
        db.commit()
        
        logger.info(f"Store deleted successfully: {store.store_name}")
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error deleting store: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the store."
        )
