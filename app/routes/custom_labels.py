from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging
from app.database import get_db
from app.models.employees import Employee
from app.models.custom_labels import CustomLabel
from app.schemas.custom_labels import (
    CustomLabelCreate,
    CustomLabelUpdate,
    CustomLabel as CustomLabelSchema
)
from app.core.dependencies import get_current_employee, require_role

router = APIRouter()
logging.basicConfig(level=logging.INFO)


@router.post("/custom-labels", response_model=CustomLabelSchema, status_code=status.HTTP_201_CREATED)
def create_custom_label(
    label_data: CustomLabelCreate,
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """
    Create a new custom label with predefined values.
    Only owner, admin, or manager can create custom labels.
    """
    # Check if label already exists for this business
    existing_label = db.query(CustomLabel).filter(
        CustomLabel.business_id == current_employee.business_id,
        CustomLabel.label_name == label_data.label_name
    ).first()
    
    if existing_label:
        raise HTTPException(
            status_code=400,
            detail=f"Label '{label_data.label_name}' already exists for this business"
        )
    
    try:
        # Create new custom label
        custom_label = CustomLabel(
            label_name=label_data.label_name,
            label_values=label_data.label_values,
            business_id=current_employee.business_id
        )
        
        db.add(custom_label)
        db.commit()
        db.refresh(custom_label)
        
        logging.info(f"Created custom label '{label_data.label_name}' with {len(label_data.label_values)} values for business {current_employee.business_id}")
        
        return custom_label
        
    except Exception as e:
        db.rollback()
        logging.error(f"Error creating custom label: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create custom label: {str(e)}")


@router.get("/custom-labels", response_model=List[CustomLabelSchema])
def get_custom_labels(
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """
    Get all custom labels for the current business.
    Returns list of labels with their predefined values.
    """
    labels = db.query(CustomLabel).filter(
        CustomLabel.business_id == current_employee.business_id
    ).order_by(CustomLabel.label_name).all()
    
    return labels


@router.get("/custom-labels/{label_id}", response_model=CustomLabelSchema)
def get_custom_label(
    label_id: int,
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """Get a specific custom label by ID"""
    label = db.query(CustomLabel).filter(
        CustomLabel.id == label_id,
        CustomLabel.business_id == current_employee.business_id
    ).first()
    
    if not label:
        raise HTTPException(status_code=404, detail="Custom label not found")
    
    return label


@router.put("/custom-labels/{label_id}", response_model=CustomLabelSchema)
def update_custom_label(
    label_id: int,
    label_data: CustomLabelUpdate,
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """
    Update a custom label's name and/or values.
    Only owner, admin, or manager can update custom labels.
    """
    label = db.query(CustomLabel).filter(
        CustomLabel.id == label_id,
        CustomLabel.business_id == current_employee.business_id
    ).first()
    
    if not label:
        raise HTTPException(status_code=404, detail="Custom label not found")
    
    try:
        # Update label name if provided
        if label_data.label_name:
            # Check if new name conflicts with existing label
            existing = db.query(CustomLabel).filter(
                CustomLabel.business_id == current_employee.business_id,
                CustomLabel.label_name == label_data.label_name,
                CustomLabel.id != label_id
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Label '{label_data.label_name}' already exists for this business"
                )
            
            label.label_name = label_data.label_name
        
        # Update values (replace, not merge)
        if label_data.label_values:
            label.label_values = label_data.label_values
        
        db.commit()
        db.refresh(label)
        
        logging.info(f"Updated custom label '{label.label_name}' for business {current_employee.business_id}")
        
        return label
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error updating custom label: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update custom label: {str(e)}")


@router.delete("/custom-labels/{label_id}", status_code=status.HTTP_200_OK)
def delete_custom_label(
    label_id: int,
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(require_role(["owner", "admin"]))
):
    """
    Delete a custom label.
    Only owner or admin can delete custom labels.
    """
    label = db.query(CustomLabel).filter(
        CustomLabel.id == label_id,
        CustomLabel.business_id == current_employee.business_id
    ).first()
    
    if not label:
        raise HTTPException(status_code=404, detail="Custom label not found")
    
    try:
        db.delete(label)
        db.commit()
        
        logging.info(f"Deleted custom label '{label.label_name}' for business {current_employee.business_id}")
        
        return {"id": label_id, "detail": "Custom label deleted successfully"}
        
    except Exception as e:
        db.rollback()
        logging.error(f"Error deleting custom label: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete custom label: {str(e)}")


@router.get("/custom-labels-names", response_model=List[str])
def get_custom_label_names(
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """
    Get all custom label names for the current business.
    Returns simple list of label names.
    """
    labels = db.query(CustomLabel.label_name).filter(
        CustomLabel.business_id == current_employee.business_id
    ).order_by(CustomLabel.label_name).all()
    
    return [label[0] for label in labels]


@router.get("/custom-labels-values/{label_name}", response_model=List[str])
def get_custom_label_values(
    label_name: str,
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """
    Get all predefined values for a specific custom label name.
    """
    label = db.query(CustomLabel).filter(
        CustomLabel.business_id == current_employee.business_id,
        CustomLabel.label_name == label_name
    ).first()
    
    if not label:
        return []
    
    return label.label_values or []
