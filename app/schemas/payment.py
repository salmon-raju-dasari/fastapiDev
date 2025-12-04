from pydantic import BaseModel, Field
from typing import Optional

class PaymentOrderRequest(BaseModel):
    user_id: str = Field(..., description="User ID (format: USR1000)")
    amount: int = Field(..., description="Amount in paise (500 rupees = 50000 paise)")

class PaymentStatusResponse(BaseModel):
    payment_completed: bool
    is_owner: bool
    message: Optional[str] = None

class PaymentOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    user_id: str

class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str = Field(..., description="Razorpay order ID")
    razorpay_payment_id: str = Field(..., description="Razorpay payment ID")
    razorpay_signature: str = Field(..., description="Razorpay signature for verification")

class PaymentVerifyResponse(BaseModel):
    success: bool
    message: str
    payment_id: Optional[str] = None
