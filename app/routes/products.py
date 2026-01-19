import datetime
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, DatabaseError, OperationalError
from pydantic import ValidationError

from app.database import get_db
from app.models.products import Products
from app.models.employees import Employee
from app.schemas.products import ProductBase, ProductResponse, ProductUpdate
from app.core.dependencies import get_current_employee, require_role
from app.services.storage_service import storage_service


router = APIRouter()
logging.basicConfig(level=logging.INFO)


def parse_exception_to_error_detail(e: Exception, context: str = "") -> dict:
    """
    Parse exception into a structured error detail dictionary with clear messages
    """
    if isinstance(e, IntegrityError):
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        if "unique constraint" in error_msg.lower() or "duplicate key" in error_msg.lower():
            if "productid" in error_msg.lower():
                return {
                    "error": "DuplicateEntryError",
                    "message": "A product with this product ID already exists in the database",
                    "field": "productid",
                    "type": "duplicate_constraint",
                    "suggestion": "Please use a different product ID"
                }
            elif "barcode" in error_msg.lower():
                return {
                    "error": "DuplicateEntryError",
                    "message": "A product with this barcode already exists in the database",
                    "field": "barcode",
                    "type": "duplicate_constraint",
                    "suggestion": "Please use a different barcode"
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
                "suggestion": "Please ensure all required fields (productid, productname, barcode, price) are provided"
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
    - productid: Required, unique, 1-100 characters
    - productname: Required, 1-500 characters
    - barcode: Required, 1-100 characters
    - price: Required, must be greater than 0, stored with 2 decimal places
    - productimages: Optional, max 5 images
    - All other fields: Optional with specific validations
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
                # Debug: Log received product data
                logging.info(f"Processing product {idx + 1}: {product.productname}")
                logging.info(f"Product has images: {product.productimages is not None}")
                if product.productimages:
                    logging.info(f"Number of images: {len(product.productimages)}")
                    logging.info(f"First image preview: {product.productimages[0][:100] if product.productimages[0] else 'None'}...")
                
                # Validate max 5 images
                if product.productimages and len(product.productimages) > 5:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "ValidationError",
                            "message": "Maximum 5 images allowed per product",
                            "field": "productimages",
                            "type": "max_limit_exceeded",
                            "current_count": len(product.productimages),
                            "max_allowed": 5
                        }
                    )
                
                # Upload images to GCS if provided
                uploaded_image_urls = []
                if product.productimages and len(product.productimages) > 0:
                    try:
                        logging.info(f"Processing {len(product.productimages)} images for upload to GCS")
                        
                        if storage_service is None:
                            raise HTTPException(
                                status_code=500,
                                detail={
                                    "error": "StorageServiceError",
                                    "message": "Google Cloud Storage is not configured. Check server logs for details.",
                                    "type": "service_unavailable"
                                }
                            )
                        
                        uploaded_image_urls = storage_service.upload_product_images(
                            product.productimages,
                            max_images=5
                        )
                        logging.info(f"Successfully uploaded {len(uploaded_image_urls)} images to GCS products folder")
                        logging.info(f"Image URLs: {uploaded_image_urls}")
                    except ValueError as ve:
                        raise HTTPException(
                            status_code=400,
                            detail={
                                "error": "ValidationError",
                                "message": str(ve),
                                "field": "productimages",
                                "type": "max_limit_exceeded"
                            }
                        )
                    except Exception as e:
                        logging.error(f"Error uploading images to GCS: {str(e)}")
                        error_message = str(e)
                        
                        # Provide more specific error messages based on the error
                        if "invalid_grant" in error_message.lower() or "jwt" in error_message.lower():
                            detail_message = "GCS credentials are invalid or expired. Please regenerate service account key from Google Cloud Console."
                        elif "permission" in error_message.lower() or "403" in error_message:
                            detail_message = "Permission denied. Service account needs Storage Object Admin role."
                        elif "not found" in error_message.lower() or "404" in error_message:
                            detail_message = f"GCS bucket '{os.getenv('GCS_BUCKET_NAME')}' not found. Please check bucket name in .env file."
                        else:
                            detail_message = f"Failed to upload images: {error_message}"
                        
                        raise HTTPException(
                            status_code=500,
                            detail={
                                "error": "ImageUploadError",
                                "message": detail_message,
                                "type": "storage_error",
                                "raw_error": error_message
                            }
                        )
                
                # Check if product with same barcode already exists
                existing_barcode = db.query(Products).filter(Products.barcode == product.barcode).first()
                if existing_barcode:
                    errors.append({
                        "product_index": idx,
                        "field": "barcode",
                        "value": product.barcode,
                        "error": f"Product with barcode '{product.barcode}' already exists",
                        "type": "duplicate_entry"
                    })
                    continue
                
                # Check if product with same SKU already exists (if SKU provided)
                if product.sku:
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
                
                # Create the product without productid (will be auto-generated after insert)
                db_product = Products(
                    business_id=str(current_user.business_id),
                    productid=None,  # Will be set after getting auto-generated ID
                    productname=product.productname,
                    barcode=product.barcode,
                    sku=product.sku,
                    description=product.description,
                    brand=product.brand,
                    category=product.category,
                    productimages=uploaded_image_urls if uploaded_image_urls else None,  # Use GCS URLs
                    price=product.price,
                    unitvalue=product.unitvalue,
                    unit=product.unit,
                    discount=product.discount,
                    gst=product.gst,
                    openingstock=product.openingstock,
                    quantity=product.openingstock if product.openingstock else 0,  # Set quantity to openingstock
                    mfgdate=product.mfgdate,
                    expirydate=product.expirydate,
                    suppliername=product.suppliername,
                    suppliercontact=product.suppliercontact,
                    customfields=product.customfields,
                    updated_by=current_user.name
                )
                db.add(db_product)
                db.flush()  # Flush to get the auto-generated id
                
                # Set productid as PRD{id} after getting auto-generated ID
                db_product.productid = f"PRD{db_product.id}"
                db.flush()  # Update with formatted productid
                
                created_products.append(db_product)
                
            except IntegrityError as ie:
                db.rollback()
                error_msg = str(ie.orig)
                
                # Parse specific database constraint errors
                if "unique constraint" in error_msg.lower() or "duplicate key" in error_msg.lower():
                    if "productid" in error_msg.lower():
                        field = "productid"
                        message = f"Product ID '{product.productid}' already exists"
                    elif "barcode" in error_msg.lower():
                        field = "barcode"
                        message = f"Barcode '{product.barcode}' already exists"
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


@router.get("/getProducts")
def get_products(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_employee)
):
    """
    Get all products with pagination - requires authentication (all roles can view)
    Returns paginated products with total count
    
    Parameters:
    - skip: Number of records to skip (for pagination)
    - limit: Number of records to return (max per page)
    """
    logging.info(f"User {current_user.name} fetching products (skip={skip}, limit={limit})")
    try:
        # Filter by business_id
        query = db.query(Products).filter(Products.business_id == str(current_user.business_id))
        
        # Get total count
        total = query.count()
        
        # Get paginated products
        products = query.offset(skip).limit(limit).all()
        
        # Convert to response format
        products_list = []
        for product in products:
            product_dict = {
                "id": product.id,
                "productid": product.productid if product.productid else f"PRD{product.id}",
                "productname": product.productname,
                "barcode": product.barcode,
                "sku": product.sku,
                "description": product.description,
                "brand": product.brand,
                "category": product.category,
                "productimages": product.productimages,
                "price": product.price,
                "unitvalue": product.unitvalue,
                "unit": product.unit,
                "discount": product.discount,
                "gst": product.gst,
                "quantity": product.quantity,
                "openingstock": product.openingstock,
                "mfgdate": product.mfgdate,
                "expirydate": product.expirydate,
                "suppliername": product.suppliername,
                "suppliercontact": product.suppliercontact,
                "customfields": product.customfields,
                "created_at": product.created_at,
                "updated_at": product.updated_at
            }
            products_list.append(product_dict)
        
        return {
            "items": products_list,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logging.error(f"Error fetching products: {str(e)}", exc_info=True)
        error_detail = parse_exception_to_error_detail(e, "fetching products")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.get("/getProduct/{product_id}", response_model=ProductResponse)
def get_product_by_id(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_employee)
):
    """
    Get a single product by ID - requires authentication
    Used for populating edit form with product details
    """
    logging.info(f"User {current_user.name} fetching product ID {product_id}")
    try:
        product = db.query(Products).filter(
            Products.id == product_id,
            Products.business_id == str(current_user.business_id)
        ).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "NotFoundError",
                    "message": f"Product with ID {product_id} not found",
                    "type": "not_found"
                }
            )
        return product
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching product ID {product_id}: {str(e)}", exc_info=True)
        error_detail = parse_exception_to_error_detail(e, f"fetching product with ID {product_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.get("/getProductByProductId/{productid}", response_model=ProductResponse)
def get_product_by_productid(
    productid: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_employee)
):
    """
    Get a single product by productid - requires authentication
    Used for searching/filtering products by productid
    """
    logging.info(f"User {current_user.name} fetching product with productid {productid}")
    try:
        product = db.query(Products).filter(
            Products.productid == productid,
            Products.business_id == str(current_user.business_id)
        ).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "NotFoundError",
                    "message": f"Product with productid '{productid}' not found",
                    "type": "not_found"
                }
            )
        return product
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching product productid {productid}: {str(e)}", exc_info=True)
        error_detail = parse_exception_to_error_detail(e, f"fetching product with productid '{productid}'")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.put("/updateProduct/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """
    Update a product by ID - requires owner, admin, or manager role
    All fields are optional - only provided fields will be updated
    Used when editing a product from the product card/form
    """
    logging.info(f"User {current_user.name} updating product ID {product_id}")
    
    try:
        product = db.query(Products).filter(
            Products.id == product_id,
            Products.business_id == str(current_user.business_id)
        ).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "NotFoundError",
                    "message": f"Product with ID {product_id} not found",
                    "type": "not_found"
                }
            )
        
        # Get only the fields that were actually provided in the update
        update_dict = product_data.model_dump(exclude_unset=True)
        
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "ValidationError",
                    "message": "No fields provided for update",
                    "type": "missing_data"
                }
            )
        
        # Check for duplicate barcode if it's being updated
        if "barcode" in update_dict and update_dict["barcode"] != product.barcode:
            existing = db.query(Products).filter(
                Products.barcode == update_dict["barcode"],
                Products.id != product_id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "DuplicateEntryError",
                        "message": f"Product with barcode '{update_dict['barcode']}' already exists",
                        "field": "barcode",
                        "type": "duplicate_entry"
                    }
                )
        
        # Check for duplicate SKU if it's being updated
        if "sku" in update_dict and update_dict["sku"] and update_dict["sku"] != product.sku:
            existing = db.query(Products).filter(
                Products.sku == update_dict["sku"],
                Products.id != product_id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "DuplicateEntryError",
                        "message": f"Product with SKU '{update_dict['sku']}' already exists",
                        "field": "sku",
                        "type": "duplicate_entry"
                    }
                )
        
        # Handle image uploads if productimages are provided
        if "productimages" in update_dict and update_dict["productimages"]:
            images = update_dict["productimages"]
            
            # Validate max 5 images
            if len(images) > 5:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "ValidationError",
                        "message": "Maximum 5 images allowed per product",
                        "field": "productimages",
                        "type": "max_limit_exceeded",
                        "current_count": len(images),
                        "max_allowed": 5
                    }
                )
            
            # Check if images are base64 (need upload) or already GCS URLs (skip upload)
            images_to_upload = []
            existing_urls = []
            
            for img in images:
                if img and img.startswith("data:image"):
                    # Base64 image - needs to be uploaded
                    images_to_upload.append(img)
                elif img and img.startswith("http"):
                    # Already a URL - keep as is
                    existing_urls.append(img)
            
            # Upload new base64 images to GCS
            if images_to_upload:
                try:
                    logging.info(f"Processing {len(images_to_upload)} new images for upload to GCS")
                    
                    if storage_service is None:
                        raise HTTPException(
                            status_code=500,
                            detail={
                                "error": "StorageServiceError",
                                "message": "Google Cloud Storage is not configured. Check server logs for details.",
                                "type": "service_unavailable"
                            }
                        )
                    
                    uploaded_urls = storage_service.upload_product_images(
                        images_to_upload,
                        max_images=5
                    )
                    logging.info(f"Successfully uploaded {len(uploaded_urls)} images to GCS products folder")
                    
                    # Combine existing URLs and newly uploaded URLs
                    update_dict["productimages"] = existing_urls + uploaded_urls
                    
                except ValueError as ve:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "ValidationError",
                            "message": str(ve),
                            "field": "productimages",
                            "type": "max_limit_exceeded"
                        }
                    )
                except Exception as e:
                    logging.error(f"Error uploading images to GCS: {str(e)}")
                    error_message = str(e)
                    
                    # Provide more specific error messages based on the error
                    if "invalid_grant" in error_message.lower() or "jwt" in error_message.lower():
                        detail_message = "GCS credentials are invalid or expired. Please regenerate service account key from Google Cloud Console."
                    elif "permission" in error_message.lower() or "403" in error_message:
                        detail_message = "Permission denied. Service account needs Storage Object Admin role."
                    elif "not found" in error_message.lower() or "404" in error_message:
                        detail_message = f"GCS bucket '{os.getenv('GCS_BUCKET_NAME')}' not found. Please check bucket name in .env file."
                    else:
                        detail_message = f"Failed to upload images: {error_message}"
                    
                    raise HTTPException(
                        status_code=500,
                        detail={
                            "error": "ImageUploadError",
                            "message": detail_message,
                            "type": "storage_error",
                            "raw_error": error_message
                        }
                    )
            else:
                # Only existing URLs, no upload needed
                update_dict["productimages"] = existing_urls
        
        # Update fields
        for key, value in update_dict.items():
            setattr(product, key, value)
        
        product.updated_by = current_user.name
        
        db.commit()
        db.refresh(product)
        
        logging.info(f"Product ID {product_id} updated successfully")
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error updating product ID {product_id}: {str(e)}", exc_info=True)
        error_detail = parse_exception_to_error_detail(e, f"updating product with ID {product_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.delete("/deleteProduct/{product_id}", status_code=status.HTTP_200_OK)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """
    Delete a product by ID - requires owner, admin, or manager role
    Used when deleting a product from the product card
    """
    logging.info(f"User {current_user.name} deleting product ID {product_id}")
    
    try:
        product = db.query(Products).filter(
            Products.id == product_id,
            Products.business_id == str(current_user.business_id)
        ).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "NotFoundError",
                    "message": f"Product with ID {product_id} not found",
                    "type": "not_found"
                }
            )
        
        product_info = {
            "id": product.id,
            "productid": product.productid,
            "productname": product.productname
        }
        
        db.delete(product)
        db.commit()
        
        logging.info(f"Product ID {product_id} deleted successfully")
        return {
            "status": "success",
            "message": f"Product deleted successfully",
            "deleted_product": product_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error deleting product ID {product_id}: {str(e)}", exc_info=True)
        error_detail = parse_exception_to_error_detail(e, f"deleting product with ID {product_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.delete("/deleteProducts", status_code=status.HTTP_200_OK)
def delete_products_bulk(
    product_ids: List[int],
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role(["owner", "admin", "manager"]))
):
    """
    Bulk delete products by IDs - requires owner, admin, or manager role
    
    Request format: [1, 2, 3, 4, 5]
    Returns detailed results for each product with success/failure status
    """
    logging.info(f"User {current_user.name} bulk deleting {len(product_ids)} product(s)")
    
    if not product_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": "No product IDs provided for deletion",
                "type": "missing_data"
            }
        )
    
    results = []
    successful_count = 0
    failed_count = 0
    
    for idx, product_id in enumerate(product_ids):
        try:
            product = db.query(Products).filter(
                Products.id == product_id,
                Products.business_id == str(current_user.business_id)
            ).first()
            if not product:
                results.append({
                    "product_index": idx,
                    "product_id": product_id,
                    "status": "failed",
                    "error": f"Product with ID {product_id} not found",
                    "type": "not_found"
                })
                failed_count += 1
                continue
            
            product_info = {
                "id": product.id,
                "productid": product.productid,
                "productname": product.productname
            }
            
            db.delete(product)
            db.commit()
            
            results.append({
                "product_index": idx,
                "product_id": product_id,
                "status": "success",
                "message": f"Product '{product_info['productname']}' deleted successfully",
                "deleted_product": product_info
            })
            successful_count += 1
            
        except Exception as e:
            db.rollback()
            error_detail = parse_exception_to_error_detail(e, f"deleting product with ID {product_id}")
            results.append({
                "product_index": idx,
                "product_id": product_id,
                "status": "failed",
                "error": error_detail.get("message", "Deletion failed"),
                "error_details": error_detail,
                "type": error_detail.get("type", "server_error")
            })
            failed_count += 1
    
    logging.info(f"Bulk delete completed: {successful_count} successful, {failed_count} failed")
    
    return {
        "summary": {
            "total": len(product_ids),
            "successful": successful_count,
            "failed": failed_count
        },
        "results": results
    }


@router.get("/searchProducts", response_model=List[ProductResponse])
def search_products(
    query: Optional[str] = None,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_employee)
):
    """
    Search and filter products - requires authentication
    
    Query parameters:
    - query: Search in productname, productid, barcode, SKU
    - category: Filter by category
    - brand: Filter by brand
    - min_price: Minimum price filter
    - max_price: Maximum price filter
    """
    logging.info(f"User {current_user.name} searching products with filters")
    
    try:
        # Filter by business_id first
        products_query = db.query(Products).filter(Products.business_id == str(current_user.business_id))
        
        # Search in multiple fields
        if query:
            search_term = f"%{query}%"
            products_query = products_query.filter(
                (Products.productname.ilike(search_term)) |
                (Products.productid.ilike(search_term)) |
                (Products.barcode.ilike(search_term)) |
                (Products.sku.ilike(search_term))
            )
        
        # Filter by category
        if category:
            products_query = products_query.filter(Products.category.ilike(f"%{category}%"))
        
        # Filter by brand
        if brand:
            products_query = products_query.filter(Products.brand.ilike(f"%{brand}%"))
        
        # Filter by price range
        if min_price is not None:
            products_query = products_query.filter(Products.price >= min_price)
        if max_price is not None:
            products_query = products_query.filter(Products.price <= max_price)
        
        products = products_query.all()
        return products
        
    except Exception as e:
        logging.error(f"Error searching products: {str(e)}", exc_info=True)
        error_detail = parse_exception_to_error_detail(e, "searching products")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )
