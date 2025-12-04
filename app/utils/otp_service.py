import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

# In-memory OTP storage
# Format: {email: {"otp": "123456", "expires_at": datetime, "user_id": "123", "purpose": "forgot_username"}}
otp_storage: Dict[str, Dict] = {}

# OTP expiration time in minutes
OTP_EXPIRY_MINUTES = 10


def generate_otp() -> str:
    """Generate a 6-digit OTP code"""
    return ''.join(random.choices(string.digits, k=6))


def store_otp(email: str, user_id: str, purpose: str) -> str:
    """
    Generate and store OTP for an email address
    
    Args:
        email: User's email address
        user_id: User ID
        purpose: Purpose of OTP (forgot_username, forgot_password)
    
    Returns:
        Generated OTP code
    """
    otp = generate_otp()
    expires_at = datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    
    otp_storage[email] = {
        "otp": otp,
        "expires_at": expires_at,
        "user_id": user_id,
        "purpose": purpose
    }
    
    logger.info(f"OTP stored for {email}, purpose: {purpose}, expires at: {expires_at}")
    return otp


def verify_otp(email: str, otp: str, purpose: str) -> Optional[str]:
    """
    Verify OTP for an email address
    
    Args:
        email: User's email address
        otp: OTP code to verify
        purpose: Purpose of OTP (forgot_username, forgot_password)
    
    Returns:
        User ID if OTP is valid, None otherwise
    """
    if email not in otp_storage:
        logger.warning(f"No OTP found for email: {email}")
        return None
    
    stored_data = otp_storage[email]
    
    # Check if OTP has expired
    if datetime.now() > stored_data["expires_at"]:
        logger.warning(f"OTP expired for email: {email}")
        del otp_storage[email]  # Clean up expired OTP
        return None
    
    # Check if OTP matches
    if stored_data["otp"] != otp:
        logger.warning(f"Invalid OTP for email: {email}")
        return None
    
    # Check if purpose matches
    if stored_data["purpose"] != purpose:
        logger.warning(f"OTP purpose mismatch for email: {email}. Expected: {purpose}, Got: {stored_data['purpose']}")
        return None
    
    # OTP is valid
    user_id = stored_data["user_id"]
    logger.info(f"OTP verified successfully for email: {email}, user_id: {user_id}")
    
    # Delete OTP after successful verification (single use)
    del otp_storage[email]
    
    return user_id


def delete_otp(email: str):
    """Delete OTP for an email address"""
    if email in otp_storage:
        del otp_storage[email]
        logger.info(f"OTP deleted for email: {email}")


def cleanup_expired_otps():
    """Clean up expired OTPs from storage"""
    now = datetime.now()
    expired_emails = [email for email, data in otp_storage.items() if now > data["expires_at"]]
    
    for email in expired_emails:
        del otp_storage[email]
    
    if expired_emails:
        logger.info(f"Cleaned up {len(expired_emails)} expired OTPs")
