from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import razorpay
import os
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta
from app.database import get_db
from app.models.payment import Payment
from app.models.employees import Employee
from app.schemas.payment import (
    PaymentOrderRequest,
    PaymentOrderResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse
)

# Load environment variables
load_dotenv()

router = APIRouter()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Razorpay credentials from environment variables
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    logger.warning("Razorpay credentials not found in environment variables!")
    raise ValueError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be set in .env file")

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


@router.get("/razorpay-key")
async def get_razorpay_key():
    """
    Get Razorpay key ID for frontend integration
    """
    return {"key_id": RAZORPAY_KEY_ID}


@router.post("/create-order", response_model=PaymentOrderResponse)
async def create_payment_order(
    request: PaymentOrderRequest,
    db: Session = Depends(get_db)
):
    """
    Create a Razorpay order for registration payment
    """
    try:
        # Verify user exists
        logger.info(f"Received payment order request for user_id: {request.user_id}")
        
        if not request.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID is required"
            )
        
        # Handle both formats: "USR123" and "123" (case-insensitive)
        emp_id_str = request.user_id.upper().replace("USR", "").strip()
        
        if not emp_id_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format. Expected format: USR1000"
            )
        
        try:
            emp_id = int(emp_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid user ID format: '{request.user_id}'. Expected format: USR1000"
            )
        
        employee = db.query(Employee).filter(Employee.emp_id == emp_id).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Only owner can create payment order
        if employee.role.lower() != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only business owner can make payment. Please contact your business owner."
            )
        
        # Check if there's an existing payment for this business (paid or unpaid)
        existing_payment = db.query(Payment).filter(
            Payment.business_id == employee.business_id
        ).first()
        
        # If payment already completed, reject
        if existing_payment and existing_payment.status == "paid" and existing_payment.verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment already completed for this business"
            )
        
        # Create Razorpay order
        order_data = {
            "amount": request.amount,  # Amount in paise
            "currency": "INR",
            "notes": {
                "user_id": request.user_id,
                "business_id": str(employee.business_id),
                "purpose": "Registration Fee"
            }
        }
        
        try:
            razorpay_order = razorpay_client.order.create(data=order_data)
        except Exception as razorpay_error:
            logger.error(f"Razorpay order creation failed: {str(razorpay_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to create payment order. Please try again in a few moments."
            )
        
        # Update existing payment or create new one
        try:
            # Set expiration: 1 month (30 days)
            expiration_time = datetime.utcnow() + timedelta(days=30)
            
            if existing_payment:
                # Update existing payment record
                logger.info(f"Updating existing payment for business {employee.business_id}")
                existing_payment.user_id = emp_id
                existing_payment.razorpay_order_id = razorpay_order["id"]
                existing_payment.amount = request.amount
                existing_payment.currency = "INR"
                existing_payment.status = "created"
                existing_payment.verified = False
                existing_payment.razorpay_payment_id = None
                existing_payment.razorpay_signature = None
                existing_payment.expires_at = expiration_time
                payment = existing_payment
            else:
                # Create new payment record
                logger.info(f"Creating new payment for business {employee.business_id}")
                payment = Payment(
                    user_id=emp_id,
                    business_id=employee.business_id,
                    razorpay_order_id=razorpay_order["id"],
                    amount=request.amount,
                    currency="INR",
                    status="created",
                    expires_at=expiration_time
                )
                db.add(payment)
            
            db.commit()
            db.refresh(payment)
        except Exception as db_error:
            logger.error(f"Database error saving payment: {str(db_error)}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Payment order created but failed to save. Please contact support."
            )
        
        logger.info(f"Payment order created: {razorpay_order['id']} for user {request.user_id}")
        
        return PaymentOrderResponse(
            order_id=razorpay_order["id"],
            amount=razorpay_order["amount"],
            currency=razorpay_order["currency"],
            user_id=request.user_id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating payment order: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process payment. Please try again or contact support if the issue persists."
        )


@router.post("/verify", response_model=PaymentVerifyResponse)
async def verify_payment(
    request: PaymentVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Verify Razorpay payment signature and update payment status
    """
    try:
        # Find payment record
        payment = db.query(Payment).filter(
            Payment.razorpay_order_id == request.razorpay_order_id
        ).first()
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment order not found"
            )
        
        # Verify payment signature using Razorpay's signature verification
        # This ensures the payment response is authentic and hasn't been tampered with
        try:
            # Method 1: Using Razorpay's utility (recommended)
            razorpay_client.utility.verify_payment_signature({
                'razorpay_order_id': request.razorpay_order_id,
                'razorpay_payment_id': request.razorpay_payment_id,
                'razorpay_signature': request.razorpay_signature
            })
            logger.info(f"Payment signature verified successfully for order {request.razorpay_order_id}")
        except razorpay.errors.SignatureVerificationError as e:
            logger.error(f"Signature verification failed for order {request.razorpay_order_id}: {str(e)}")
            # Update payment status to failed
            payment.status = "failed"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment signature. Payment verification failed."
            )
        
        # Fetch payment details from Razorpay
        try:
            razorpay_payment = razorpay_client.payment.fetch(request.razorpay_payment_id)
        except Exception as e:
            logger.error(f"Error fetching payment from Razorpay: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify payment with Razorpay"
            )
        
        # Update payment record with new expiry date (extend by 1 month)
        payment.razorpay_payment_id = request.razorpay_payment_id
        payment.razorpay_signature = request.razorpay_signature
        payment.status = "paid"
        payment.verified = True
        payment.payment_method = razorpay_payment.get("method")
        payment.payment_email = razorpay_payment.get("email")
        payment.payment_contact = razorpay_payment.get("contact")
        payment.expires_at = datetime.utcnow() + timedelta(days=30)  # Extend expiry by 1 month
        
        db.commit()
        
        logger.info(f"Payment verified successfully: {request.razorpay_payment_id} for order {request.razorpay_order_id}")
        
        return PaymentVerifyResponse(
            success=True,
            message="Payment verified successfully",
            payment_id=request.razorpay_payment_id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying payment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment verification failed: {str(e)}"
        )


@router.get("/status/{user_id}")
async def get_payment_status(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Check if user's business has completed payment
    """
    try:
        # Convert USR prefix to integer emp_id (case-insensitive)
        emp_id_str = user_id.upper().replace("USR", "")
        try:
            emp_id = int(emp_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )
        
        # Get employee details
        employee = db.query(Employee).filter(Employee.emp_id == emp_id).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if payment completed for this business
        payment = db.query(Payment).filter(
            Payment.business_id == employee.business_id,
            Payment.status == "paid",
            Payment.verified == True
        ).first()
        
        is_owner = employee.role.lower() == "owner"
        
        if payment:
            # Check if payment has expired
            current_time = datetime.utcnow()
            if payment.expires_at and current_time > payment.expires_at:
                # Payment expired - mark as expired and return as not completed
                logger.info(f"Payment expired for business {employee.business_id}. Expiry time: {payment.expires_at}")
                payment.status = "expired"
                db.commit()
                
                message = None
                if not is_owner:
                    message = "Payment expired. Please contact your business owner to renew the subscription."
                else:
                    message = "Your payment has expired. Please renew your subscription."
                
                return {
                    "payment_completed": False,
                    "is_owner": is_owner,
                    "message": message,
                    "expired": True,
                    "expired_at": payment.expires_at
                }
            
            # Payment still valid
            return {
                "payment_completed": True,
                "is_owner": is_owner,
                "payment_id": payment.razorpay_payment_id,
                "amount": payment.amount,
                "paid_at": payment.updated_at,
                "expires_at": payment.expires_at
            }
        else:
            message = None
            if not is_owner:
                message = "Payment pending. Please contact your business owner to complete the registration payment."
            
            return {
                "payment_completed": False,
                "is_owner": is_owner,
                "message": message
            }
    
    except Exception as e:
        logger.error(f"Error checking payment status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check payment status"
        )
