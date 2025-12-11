import logging
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
        
        logger.info(f"=== CREATE STORE called by user: {current_user.name} (ID: {current_user.emp_id}) ===")
        logger.info(f"Current user business_id: {current_user.business_id}")
        logger.info(f"Store data received: {store_data.dict()}")
        
        # Use current user's business_id
        user_business_id = str(current_user.business_id)
        
        # Verify business exists
        business = db.query(Business).filter(Business.business_id == user_business_id).first()
        if not business:
            logger.error(f"Business not found for business_id: {user_business_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Your business profile was not found. Please contact support."
            )
        
        logger.info(f"Creating store for business: {business.business_name} (ID: {business.business_id})")
        
        # Get the next sequence number for this business
        max_sequence = db.query(Store).filter(
            Store.business_id == user_business_id
        ).count()
        next_sequence = max_sequence + 1
        
        logger.info(f"Next store sequence for business {user_business_id}: {next_sequence}")
        
        # Create store with user's business_id and sequence
        db_store = Store(
            **store_data.dict(),
            business_id=user_business_id,
            store_sequence=next_sequence
        )
        
        logger.info(f"Store object created - business_id: {user_business_id}, sequence: {next_sequence}")
        db.add(db_store)
        db.commit()
        db.refresh(db_store)
        
        logger.info(f"Store created successfully: {db_store.store_name} (ID: {db_store.id}, Store ID: STR{db_store.store_sequence})")
        
        # Return formatted response
        return {
            "id": db_store.id,
            "business_id": db_store.business_id,
            "store_id": f"STR{db_store.store_sequence}",
            "store_sequence": db_store.store_sequence,
            "store_name": db_store.store_name,
            "store_address": db_store.store_address,
            "store_city": db_store.store_city,
            "store_state": db_store.store_state,
            "store_country": db_store.store_country,
            "store_pincode": db_store.store_pincode,
            "created_at": db_store.created_at,
            "updated_at": db_store.updated_at
        }
    
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while creating store: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A store with this name already exists. Please use a different store name."
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating store: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the store. Please try again."
        )

@router.get("/", response_model=dict)
async def get_stores(
    skip: int = 0,
    limit: int = 100,
    filters: str = None,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_employee)
):
    """Get all stores with pagination and filtering - all authenticated users can view"""
    import json
    
    try:
        logger.info(f"=== GET /stores called by user: {current_user.name} (ID: {current_user.emp_id}) ===")
        logger.info(f"Filters: {filters}, Skip: {skip}, Limit: {limit}")
        
        # Start with base query - filter by business_id
        query = db.query(Store).filter(Store.business_id == str(current_user.business_id))
        
        # Parse multiple filters if provided
        filter_list = []
        if filters:
            try:
                filter_list = json.loads(filters)
            except:
                pass
        
        # Apply multiple filters with AND logic
        if filter_list:
            for filter_item in filter_list:
                filter_field_item = filter_item.get('field')
                filter_value_item = filter_item.get('value')
                
                if not filter_field_item or not filter_value_item:
                    continue
                
                # Apply filter based on field
                if filter_field_item == "store_name":
                    query = query.filter(Store.store_name.ilike(f"%{filter_value_item}%"))
                elif filter_field_item == "store_city":
                    query = query.filter(Store.store_city.ilike(f"%{filter_value_item}%"))
                elif filter_field_item == "store_state":
                    query = query.filter(Store.store_state.ilike(f"%{filter_value_item}%"))
                elif filter_field_item == "store_country":
                    query = query.filter(Store.store_country.ilike(f"%{filter_value_item}%"))
                elif filter_field_item == "store_pincode":
                    query = query.filter(Store.store_pincode.ilike(f"%{filter_value_item}%"))
        
        # Get total count after filtering
        total = query.count()
        
        # Apply pagination and ordering
        stores = query.order_by(Store.store_sequence).offset(skip).limit(limit).all()
        
        # Format response with store_id
        store_responses = []
        for store in stores:
            store_dict = {
                "id": store.id,
                "business_id": store.business_id,
                "store_id": f"STR{store.store_sequence}",
                "store_sequence": store.store_sequence,
                "store_name": store.store_name,
                "store_address": store.store_address,
                "store_city": store.store_city,
                "store_state": store.store_state,
                "store_country": store.store_country,
                "store_pincode": store.store_pincode,
                "created_at": store.created_at,
                "updated_at": store.updated_at
            }
            store_responses.append(store_dict)
        
        logger.info(f"Returning {len(store_responses)} of {total} stores")
        
        return {
            "items": store_responses,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error fetching stores: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while loading stores."
        )

@router.get("/{store_id}", response_model=StoreResponse)
async def get_store(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_employee)
):
    """Get a specific store by ID"""
    try:
        store = db.query(Store).filter(
            Store.id == store_id,
            Store.business_id == str(current_user.business_id)
        ).first()
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store with ID {store_id} not found."
            )
        
        # Return formatted response
        return {
            "id": store.id,
            "business_id": store.business_id,
            "store_id": f"STR{store.store_sequence}",
            "store_sequence": store.store_sequence,
            "store_name": store.store_name,
            "store_address": store.store_address,
            "store_city": store.store_city,
            "store_state": store.store_state,
            "store_country": store.store_country,
            "store_pincode": store.store_pincode,
            "created_at": store.created_at,
            "updated_at": store.updated_at
        }
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
    store_id: int,
    store_data: StoreUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role(["owner", "admin"]))
):
    """Update store details - owner and admin can update"""
    try:
        store = db.query(Store).filter(
            Store.id == store_id,
            Store.business_id == str(current_user.business_id)
        ).first()
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
        
        # Return formatted response
        return {
            "id": store.id,
            "business_id": store.business_id,
            "store_id": f"STR{store.store_sequence}",
            "store_sequence": store.store_sequence,
            "store_name": store.store_name,
            "store_address": store.store_address,
            "store_city": store.store_city,
            "store_state": store.store_state,
            "store_country": store.store_country,
            "store_pincode": store.store_pincode,
            "created_at": store.created_at,
            "updated_at": store.updated_at
        }
    
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while updating store: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A store with this name already exists. Please use a different store name."
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
    store_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role(["owner", "admin"]))
):
    """Delete a store - only owner and admin can delete"""
    try:
        store = db.query(Store).filter(
            Store.id == store_id,
            Store.business_id == str(current_user.business_id)
        ).first()
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
