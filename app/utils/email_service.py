import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Email configuration - set these as environment variables
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "salmonrajudasaris@gmail.com")  # Your email
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "dkgb ylkc qybb fvtg")  # Your email password or app password
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)
APP_NAME = os.getenv("APP_NAME", "supermarket")

def send_email(to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
    """
    Send an email using SMTP
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content of the email
        text_content: Plain text content (optional, defaults to stripped HTML)
    
    Returns:
        True if email sent successfully, False otherwise
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning(f"SMTP credentials not configured. Email to {to_email} not sent. Please configure SMTP_USER and SMTP_PASSWORD environment variables.")
        logger.info(f"Email would have been sent to: {to_email}")
        logger.info(f"Subject: {subject}")
        return False
    
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = FROM_EMAIL
        message["To"] = to_email
        
        # Create plain text version if not provided
        if not text_content:
            text_content = html_content.replace("<br>", "\n").replace("</p>", "\n")
        
        # Attach both plain text and HTML versions
        part1 = MIMEText(text_content, "plain")
        part2 = MIMEText(html_content, "html")
        message.attach(part1)
        message.attach(part2)
        
        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(message)
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False


def send_registration_email(to_email: str, user_name: str, user_id: str, role: str, business_id: int = None, password: str = None) -> bool:
    """
    Send registration confirmation email with login credentials
    
    Args:
        to_email: Recipient email address
        user_name: Name of the registered user
        user_id: User ID for login
        role: User role (owner, admin, employee, etc.)
        business_id: Business ID (optional)
        password: Plain text password (optional, only sent when creating account for user)
    
    Returns:
        True if email sent successfully, False otherwise
    """
    subject = f"Welcome to {APP_NAME} - Registration Successful"
    
    password_section = ""
    if password:
        password_section = f"""
                    <p><strong>Password:</strong> {password}</p>
                    <p style="color: #ff9800;"><strong>⚠️ Important:</strong> Please change your password after first login for security.</p>
        """
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                <h2 style="color: #4CAF50;">Welcome to {APP_NAME}!</h2>
                <p>Dear {user_name},</p>
                <p>Your account has been successfully created. Here are your login credentials:</p>
                <div style="background-color: #f5f5f5; padding: 15px; border-left: 4px solid #4CAF50; margin: 20px 0;">
                    <p><strong>User ID:</strong> {user_id}</p>
                    <p><strong>Business ID:</strong> {business_id}</p>
                    <p><strong>Role:</strong> {role.title()}</p>
                    <p><strong>Email:</strong> {to_email}</p>
                    {password_section}
                </div>
                <p><strong>Important:</strong> Please keep your User ID and password safe. You will need them to log in to the system.</p>
                <p>If you did not create this account, please contact support immediately.</p>
                <br>
                <p>Best regards,<br>
                {APP_NAME} Team</p>
            </div>
        </body>
    </html>
    """
    
    return send_email(to_email, subject, html_content)


def send_password_reset_email(to_email: str, user_name: str, reset_token: str, user_id: str) -> bool:
    """
    Send password reset email with reset link
    
    Args:
        to_email: Recipient email address
        user_name: Name of the user
        reset_token: Password reset token
        user_id: User ID
    
    Returns:
        True if email sent successfully, False otherwise
    """
    # Base URL for your application - set as environment variable
    BASE_URL = os.getenv("BASE_URL", "http://localhost:3000")
    reset_link = f"{BASE_URL}/reset-password?token={reset_token}&user_id={user_id}"
    
    subject = f"{APP_NAME} - Password Reset Request"
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                <h2 style="color: #FF9800;">Password Reset Request</h2>
                <p>Dear {user_name},</p>
                <p>We received a request to reset your password for your {APP_NAME} account.</p>
                <p><strong>User ID:</strong> {user_id}</p>
                <p>Click the button below to reset your password:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" 
                       style="background-color: #4CAF50; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #4CAF50;">{reset_link}</p>
                <p><strong>Important:</strong> This link will expire in 1 hour.</p>
                <p>If you did not request a password reset, please ignore this email or contact support if you have concerns.</p>
                <br>
                <p>Best regards,<br>
                {APP_NAME} Team</p>
            </div>
        </body>
    </html>
    """
    
    return send_email(to_email, subject, html_content)


def send_otp_email(to_email: str, user_name: str, otp: str, purpose: str) -> bool:
    """
    Send OTP verification email
    
    Args:
        to_email: Recipient email address
        user_name: Name of the user
        otp: 6-digit OTP code
        purpose: Purpose of OTP (e.g., "verify your identity", "reset password")
    
    Returns:
        True if email sent successfully, False otherwise
    """
    subject = f"{APP_NAME} - Verification Code"
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                <h2 style="color: #4CAF50;">Verification Code</h2>
                <p>Dear {user_name},</p>
                <p>You requested to {purpose}. Please use the following verification code:</p>
                <div style="background-color: #f5f5f5; padding: 20px; border-left: 4px solid #4CAF50; margin: 20px 0; text-align: center;">
                    <h1 style="color: #4CAF50; font-size: 36px; margin: 0; letter-spacing: 8px;">{otp}</h1>
                </div>
                <p><strong>Important:</strong> This code will expire in 10 minutes.</p>
                <p>If you did not request this code, please ignore this email or contact support if you have concerns.</p>
                <br>
                <p>Best regards,<br>
                {APP_NAME} Team</p>
            </div>
        </body>
    </html>
    """
    
    return send_email(to_email, subject, html_content)


def send_credentials_email(to_email: str, user_name: str, user_ids: list = None, user_id: str = None, new_password: str = None) -> bool:
    """
    Send user credentials email (username recovery or password reset)
    Can send single user_id or multiple user_ids for users with same email in different businesses
    
    Args:
        to_email: Recipient email address
        user_name: Name of the user
        user_ids: List of dicts with user_id, role, business_id (for forgot username)
        user_id: Single user ID (for backward compatibility)
        new_password: New temporary password (if password was reset)
    
    Returns:
        True if email sent successfully, False otherwise
    """
    subject = f"{APP_NAME} - Your Login Credentials"
    
    password_info = ""
    if new_password:
        password_info = f"""
                    <p><strong>New Temporary Password:</strong> {new_password}</p>
                    <p style="color: #ff9800;"><strong>⚠️ Important:</strong> Please change this password after logging in for security.</p>
        """
    
    # Handle multiple user IDs (forgot username scenario)
    user_ids_html = ""
    if user_ids and len(user_ids) > 1:
        user_ids_html = "<p>You have multiple accounts with this email address:</p><ul>"
        for uid_info in user_ids:
            store_info = ""
            if uid_info.get('store_name'):
                store_info = f" - <strong>Store:</strong> {uid_info['store_name']} ({uid_info['store_id']})"
            elif uid_info.get('store_id'):
                store_info = f" - <strong>Store:</strong> {uid_info['store_id']}"
            user_ids_html += f"""<li><strong>User ID:</strong> {uid_info['user_id']} - <strong>Role:</strong> {uid_info['role'].title()} - <strong>Business ID:</strong> {uid_info['business_id']}{store_info}</li>"""
        user_ids_html += "</ul><p>Please use the appropriate User ID based on which business you want to access.</p>"
    elif user_ids and len(user_ids) == 1:
        store_info = ""
        if user_ids[0].get('store_name'):
            store_info = f"<p><strong>Store:</strong> {user_ids[0]['store_name']} ({user_ids[0]['store_id']})</p>"
        elif user_ids[0].get('store_id'):
            store_info = f"<p><strong>Store:</strong> {user_ids[0]['store_id']}</p>"
        user_ids_html = f"""<p><strong>User ID:</strong> {user_ids[0]['user_id']}</p><p><strong>Business ID:</strong> {user_ids[0]['business_id']}</p>{store_info}"""
    elif user_id:
        user_ids_html = f"""<p><strong>User ID:</strong> {user_id}</p>"""
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                <h2 style="color: #4CAF50;">Your Login Credentials</h2>
                <p>Dear {user_name},</p>
                <p>As requested, here are your login credentials:</p>
                <div style="background-color: #f5f5f5; padding: 15px; border-left: 4px solid #4CAF50; margin: 20px 0;">
                    {user_ids_html}
                    <p><strong>Email:</strong> {to_email}</p>
                    {password_info}
                </div>
                <p>You can use these credentials to log in to your account.</p>
                <p>If you did not request this information, please contact support immediately.</p>
                <br>
                <p>Best regards,<br>
                {APP_NAME} Team</p>
            </div>
        </body>
    </html>
    """
    
    return send_email(to_email, subject, html_content)
