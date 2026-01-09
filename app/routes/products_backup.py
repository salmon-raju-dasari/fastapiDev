import datetime
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, DatabaseError, OperationalError
from pydantic import ValidationError

from app.database import get_db
from app.models.products import Products
from app.models.employees import Employee
from app.schemas.products import ProductBase, ProductResponse, ProductUpdate
from app.core.dependencies import get_current_employee, require_role


router = APIRouter()
logging.basicConfig(level=logging.INFO)


def parse_exception_to_error_detail(e: Exception, context: str = "") -> dict:
    """
    Parse exception into a structured error detail dictionary with clear messages
    """
    if isinstance(e, IntegrityError):
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        if "unique constraint" in error_msg.lower() or "duplicate key" in error_msg.lower():
            if "name" in error_msg.lower():
                return {
                    "error": "DuplicateEntryError",
                    "message": "A product with this name already exists in the database",
                    "field": "name",
                    "type": "duplicate_constraint",
                    "suggestion": "Please use a different product name"
                }
            elif "sku" in error_msg.lower():
                return {
                    "error": "DuplicateEntryError",
                    "message": "A product with this SKU already exists in the database",
                    "field": "sku",
                    "type": "duplicate_constraint",
                    "suggestion": "Please use a different SKU"
                }
            else:
                return {
                    "error": "DuplicateEntryError",
                    "message": "This product already exists in the database",
                    "type": "duplicate_constraint",
                    "suggestion": "Please check your data for duplicate values"
                }
        elif "not null" in error_msg.lower() or "null value" in error_msg.lower():
            return {
                "error": "MissingRequiredFieldError",
                "message": "One or more required fields are missing",
                "type": "missing_field",
                "suggestion": "Please ensure all required fields (name, price, quantity, sku) are provided"
            }
        elif "foreign key" in error_msg.lower():
            return {
                "error": "ForeignKeyConstraintError",
                "message": "Referenced data does not exist",
                "type": "foreign_key_violation",
                "suggestion": "Please ensure all referenced data exists before creating this product"
            }
        else:
            return {
                "error": "DatabaseConstraintError",
                "message": "Database constraint violation occurred",
                "type": "constraint_violation",
                "suggestion": "Please check your data meets all database requirements"
            }
    
    elif isinstance(e, OperationalError):
        return {
            "error": "DatabaseConnectionError",
            "message": "Unable to connect to the database or query execution failed",
            "type": "database_connection",
            "suggestion": "Please try again later or contact system administrator"
        }
    
    elif isinstance(e, DatabaseError):
        return {
            "error": "DatabaseError",
            "message": "A database error occurred while processing your request",
            "type": "database_error",
            "suggestion": "Please verify your data and try again"
        }
    
    elif isinstance(e, ValidationError):
        return {
            "error": "ValidationError",
            "message": "Product data validation failed",
            "type": "validation_error",
            "validation_details": e.errors(),
            "suggestion": "Please check your product data format and required fields"
        }
    
    elif isinstance(e, ValueError):
        return {
            "error": "ValueError",
            "message": str(e) or "Invalid value provided",
            "type": "value_error",
            "suggestion": "Please check the data types and values of your input"
        }
    
    elif isinstance(e, AttributeError):
        return {
            "error": "AttributeError",
            "message": "Invalid attribute or missing field in product data",
            "type": "attribute_error",
            "suggestion": "Please ensure all required fields are properly formatted"
        }
    
    else:
        # Generic error handling
        error_message = str(e) if str(e) else "An unexpected error occurred"
        return {
            "error": "InternalServerError",
            "message": f"An unexpected error occurred while {context}" if context else error_message,
            "type": "server_error",
            "suggestion": "Please try again or contact support if the issue persists"
        }

@router.post("/addProducts", response_model=List[ProductResponse], status_code=status.HTTP_201_CREATED)
def add_products(
    products: List[ProductBase], 
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """
    Add new products - requires owner, admin, or manager role
    
    Validates all required fields and returns meaningful error messages:
    - name: Required, 1-100 characters
    - price: Required, must be greater than 0
    - quantity: Required, must be 0 or greater
    - sku: Required, unique, 1-50 characters
    - description: Optional, max 255 characters
    - category: Optional, max 50 characters
    """
    logging.info(f"User {current_user.name} adding {len(products)} product(s)")
    
    if not products:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": "No products provided",
                "field": "products",
                "type": "missing_data"
            }
        )
    
    try:
        created_products = []
        errors = []
        
        for idx, product in enumerate(products):
            try:
                # Check if product with same name already exists
                existing_name = db.query(Products).filter(Products.name == product.name).first()
                if existing_name:
                    errors.append({
                        "product_index": idx,
                        "field": "name",
                        "value": product.name,
                        "error": f"Product with name '{product.name}' already exists",
                        "type": "duplicate_entry"
                    })
                    continue
                
                # Check if product with same SKU already exists
                existing_sku = db.query(Products).filter(Products.sku == product.sku).first()
                if existing_sku:
                    errors.append({
                        "product_index": idx,
                        "field": "sku",
                        "value": product.sku,
                        "error": f"Product with SKU '{product.sku}' already exists",
                        "type": "duplicate_entry"
                    })
                    continue
                
                # Create the product
                db_product = Products(
                    name=product.name,
                    description=product.description,
                    price=product.price,
                    category=product.category,
                    quantity=product.quantity,
                    sku=product.sku,
                    updated_by=current_user.name
                    # id, created_at and updated_at are automatically set by the database
                )
                db.add(db_product)
                db.flush()  # Flush to get the auto-generated id and catch DB errors
                created_products.append(db_product)
                
            except IntegrityError as ie:
                db.rollback()
                error_msg = str(ie.orig)
                
                # Parse specific database constraint errors
                if "unique constraint" in error_msg.lower() or "duplicate key" in error_msg.lower():
                    if "name" in error_msg.lower():
                        field = "name"
                        message = f"Product name '{product.name}' already exists"
                    elif "sku" in error_msg.lower():
                        field = "sku"
                        message = f"SKU '{product.sku}' already exists"
                    else:
                        field = "unknown"
                        message = "Duplicate entry detected"
                    
                    errors.append({
                        "product_index": idx,
                        "field": field,
                        "value": getattr(product, field, "N/A"),
                        "error": message,
                        "type": "database_constraint"
                    })
                elif "not null" in error_msg.lower():
                    errors.append({
                        "product_index": idx,
                        "field": "unknown",
                        "error": "Required field is missing",
                        "type": "missing_required_field",
                        "details": error_msg
                    })
                else:
                    errors.append({
                        "product_index": idx,
                        "error": "Database error occurred",
                        "type": "database_error",
                        "details": error_msg
                    })
                continue
        
        # If there are errors, rollback and return them
        if errors:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "ProductValidationError",
                    "message": f"Failed to add {len(errors)} out of {len(products)} product(s)",
                    "successful_count": len(created_products),
                    "failed_count": len(errors),
                    "validation_errors": errors
                }
            )
        
        # Commit all successful products
        db.commit()
        
        # Refresh all products to get the final timestamps
        for p in created_products:
            db.refresh(p)
        
        logging.info(f"Successfully added {len(created_products)} product(s)")
        return created_products
        
    except HTTPException:
        # Re-raise HTTPException as is
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Unexpected error adding products: {str(e)}", exc_info=True)
        error_detail = parse_exception_to_error_detail(e, "adding products")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )

@router.get("/getProducts", response_model=List[ProductResponse])
def get_products(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_employee)
):
    """Get all products - requires authentication (all roles can view)"""
    logging.info(f"User {current_user.name} fetching all products")
    try:
        products = db.query(Products).all()
        return products
    except Exception as e:
        logging.error(f"Error fetching products: {str(e)}", exc_info=True)
        error_detail = parse_exception_to_error_detail(e, "fetching products")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )
    


# @router.put("/updateProduct/{sku}", response_model=ProductResponse)
# def update_product(
#     sku: str,
#     product_data: ProductBase,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(require_role(["admin", "manager"]))
# ):
#     """Update a product by SKU - requires admin or manager role"""
#     logging.info(f"User {current_user.username} updating product SKU {sku}")
#     try:
#         product = db.query(Products).filter(Products.sku == sku).first()
#         if not product:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail={
#                     "error": "NotFoundError",
#                     "message": f"Product with SKU {sku} not found",
#                     "type": "not_found"
#                 }
#             )
#         # Update fields
#         for key, value in product_data.model_dump().items():
#             setattr(product, key, value)
#         product.updated_by = current_user.username
#         db.commit()
#         db.refresh(product)
#         logging.info(f"Product SKU {sku} updated successfully")
#         return product
#     except HTTPException:
#         raise
#     except Exception as e:
#         db.rollback()
#         logging.error(f"Error updating product SKU {sku}: {str(e)}", exc_info=True)
#         error_detail = parse_exception_to_error_detail(e, f"updating product with SKU '{sku}'")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=error_detail
#         )

# @router.delete("/deleteProduct/{sku}", status_code=status.HTTP_204_NO_CONTENT)
# def delete_product(
#     sku: str,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(require_role(["admin", "manager"]))
# ):
#     """Delete a product by SKU - requires admin or manager role"""
#     logging.info(f"User {current_user.username} deleting product SKU {sku}")
#     try:
#         product = db.query(Products).filter(Products.sku == sku).first()
#         if not product:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail={
#                     "error": "NotFoundError",
#                     "message": f"Product with SKU {sku} not found",
#                     "type": "not_found"
#                 }
#             )
#         db.delete(product)
#         db.commit()
#         logging.info(f"Product SKU {sku} deleted successfully")
#         return
#     except HTTPException:
#         raise
#     except Exception as e:
#         db.rollback()
#         logging.error(f"Error deleting product SKU {sku}: {str(e)}", exc_info=True)
#         error_detail = parse_exception_to_error_detail(e, f"deleting product with SKU '{sku}'")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=error_detail
#         )

@router.put("/updateProducts", status_code=status.HTTP_200_OK)
def update_products_bulk(
    updates: List[dict],
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """
    Bulk update products by SKU - requires owner, admin, or manager role
    
    Request format: [
        {
            "current_sku": "PROD001",  // SKU to find the product
            "updates": {               // Fields to update (all optional)
                "name": "New Name",
                "sku": "NEW_SKU",      // Can update SKU to a new value
                "price": 999.99,
                "quantity": 100,
                "category": "New Category",
                "description": "New description"
            }
        },
        ...
    ]
    
    Returns detailed results for each product with success/failure status.
    You can update name and SKU - the system will check for duplicates before updating.
    """
    logging.info(f"User {current_user.name} bulk updating {len(updates)} product(s)")
    
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": "No products provided for update",
                "type": "missing_data"
            }
        )
    
    results = []
    successful_count = 0
    failed_count = 0
    
    for idx, item in enumerate(updates):
        current_sku = item.get("current_sku")
        update_data = item.get("updates")
        
        if not current_sku:
            results.append({
                "product_index": idx,
                "current_sku": current_sku,
                "status": "failed",
                "error": "Missing current_sku field to identify the product",
                "type": "missing_data"
            })
            failed_count += 1
            continue
        
        if not update_data:
            results.append({
                "product_index": idx,
                "current_sku": current_sku,
                "status": "failed",
                "error": "Missing updates field with data to update",
                "type": "missing_data"
            })
            failed_count += 1
            continue
        
        try:
            # Find product by current SKU
            product = db.query(Products).filter(Products.sku == current_sku).first()
            if not product:
                results.append({
                    "product_index": idx,
                    "current_sku": current_sku,
                    "status": "failed",
                    "error": f"Product with SKU '{current_sku}' not found",
                    "type": "not_found"
                })
                failed_count += 1
                continue
            
            # Validate update data
            try:
                validated = ProductUpdate(**update_data)
            except Exception as ve:
                error_detail = parse_exception_to_error_detail(ve, f"validating update data for product with SKU '{current_sku}'")
                results.append({
                    "product_index": idx,
                    "current_sku": current_sku,
                    "status": "failed",
                    "error": error_detail.get("message", "Validation failed"),
                    "error_details": error_detail,
                    "type": "validation_error"
                })
                failed_count += 1
                continue
            
            # Check for duplicate name if name is being updated
            if validated.name and validated.name != product.name:
                existing_name = db.query(Products).filter(
                    Products.name == validated.name,
                    Products.id != product.id
                ).first()
                if existing_name:
                    results.append({
                        "product_index": idx,
                        "current_sku": current_sku,
                        "status": "failed",
                        "error": f"Product with name '{validated.name}' already exists",
                        "field": "name",
                        "type": "duplicate_entry"
                    })
                    failed_count += 1
                    continue
            
            # Check for duplicate SKU if SKU is being updated
            if validated.sku and validated.sku != product.sku:
                existing_sku = db.query(Products).filter(
                    Products.sku == validated.sku,
                    Products.id != product.id
                ).first()
                if existing_sku:
                    results.append({
                        "product_index": idx,
                        "current_sku": current_sku,
                        "status": "failed",
                        "error": f"Product with SKU '{validated.sku}' already exists",
                        "field": "sku",
                        "type": "duplicate_entry"
                    })
                    failed_count += 1
                    continue
            
            # Update only provided fields
            update_dict = validated.model_dump(exclude_unset=True)
            for key, value in update_dict.items():
                setattr(product, key, value)
            
            product.updated_by = current_user.name
            
            db.commit()
            db.refresh(product)
            
            results.append({
                "product_index": idx,
                "current_sku": current_sku,
                "new_sku": product.sku,
                "status": "success",
                "product": ProductResponse.model_validate(product).model_dump(),
                "message": f"Product updated successfully (old SKU: '{current_sku}', new SKU: '{product.sku}')"
            })
            successful_count += 1
            
        except Exception as e:
            db.rollback()
            error_detail = parse_exception_to_error_detail(e, f"updating product with SKU '{current_sku}'")
            results.append({
                "product_index": idx,
                "current_sku": current_sku,
                "status": "failed",
                "error": error_detail.get("message", "Update failed"),
                "error_details": error_detail,
                "type": error_detail.get("type", "server_error")
            })
            failed_count += 1
    
    logging.info(f"Bulk update completed: {successful_count} successful, {failed_count} failed")
    
    return {
        "summary": {
            "total": len(updates),
            "successful": successful_count,
            "failed": failed_count
        },
        "results": results
    }

@router.delete("/deleteProducts", status_code=status.HTTP_200_OK)
def delete_products_bulk(
    skus: List[str],
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """
    Bulk delete products by SKU - requires owner, admin, or manager role
    
    Request format: ["SKU001", "SKU002", ...]
    Returns detailed results for each product with success/failure status
    """
    logging.info(f"User {current_user.name} bulk deleting {len(skus)} product(s)")
    
    if not skus:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": "No SKUs provided for deletion",
                "type": "missing_data"
            }
        )
    
    results = []
    successful_count = 0
    failed_count = 0
    
    for idx, sku in enumerate(skus):
        if not sku or not sku.strip():
            results.append({
                "product_index": idx,
                "sku": sku,
                "status": "failed",
                "error": "SKU is empty or invalid",
                "type": "invalid_sku"
            })
            failed_count += 1
            continue
        
        try:
            product = db.query(Products).filter(Products.sku == sku).first()
            if not product:
                results.append({
                    "product_index": idx,
                    "sku": sku,
                    "status": "failed",
                    "error": f"Product with SKU '{sku}' not found",
                    "type": "not_found"
                })
                failed_count += 1
                continue
            
            db.delete(product)
            db.commit()
            
            results.append({
                "product_index": idx,
                "sku": sku,
                "status": "success",
                "message": f"Product '{sku}' deleted successfully"
            })
            successful_count += 1
            
        except Exception as e:
            db.rollback()
            error_detail = parse_exception_to_error_detail(e, f"deleting product with SKU '{sku}'")
            results.append({
                "product_index": idx,
                "sku": sku,
                "status": "failed",
                "error": error_detail.get("message", "Deletion failed"),
                "error_details": error_detail,
                "type": error_detail.get("type", "server_error")
            })
            failed_count += 1
    
    logging.info(f"Bulk delete completed: {successful_count} successful, {failed_count} failed")
    
    return {
        "summary": {
            "total": len(skus),
            "successful": successful_count,
            "failed": failed_count
        },
        "results": results
    }