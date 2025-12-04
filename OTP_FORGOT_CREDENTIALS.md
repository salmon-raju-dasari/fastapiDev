# OTP-Based Forgot Username/Password Implementation

## Overview
This document describes the OTP (One-Time Password) based credential recovery system for the supermarket application.

## Features Implemented

### 1. Forgot Username Flow
- User enters their email address
- System generates 6-digit OTP and sends to email
- OTP valid for 10 minutes
- User enters OTP to verify identity
- System sends username (User ID) to email

### 2. Forgot Password Flow
- User enters their email address
- System generates 6-digit OTP and sends to email
- OTP valid for 10 minutes
- User enters OTP to verify identity
- System generates temporary password, updates in database
- System sends username and temporary password to email

## API Endpoints

### 1. POST /employees/forgot-username-otp
**Purpose:** Request OTP for username recovery

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "If the email is registered, an OTP will be sent."
}
```

**Security:** Does not reveal if email exists in system

---

### 2. POST /employees/forgot-password-otp
**Purpose:** Request OTP for password recovery

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "If the email is registered, an OTP will be sent."
}
```

**Security:** Does not reveal if email exists in system

---

### 3. POST /employees/verify-otp-username
**Purpose:** Verify OTP and send username to email

**Request Body:**
```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

**Response:**
```json
{
  "message": "OTP verified successfully. Your username has been sent to your email."
}
```

**Error Response:**
```json
{
  "detail": "Invalid or expired OTP"
}
```

---

### 4. POST /employees/verify-otp-password
**Purpose:** Verify OTP and send temporary password to email

**Request Body:**
```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

**Response:**
```json
{
  "message": "OTP verified successfully. A temporary password has been sent to your email."
}
```

**Error Response:**
```json
{
  "detail": "Invalid or expired OTP"
}
```

**Important:** This endpoint generates a new temporary password and updates it in the database.

## Implementation Details

### OTP Service (`app/utils/otp_service.py`)
- **Storage:** In-memory dictionary (for production, consider Redis or database)
- **OTP Generation:** 6-digit random number
- **Expiration:** 10 minutes
- **Single Use:** OTP deleted after successful verification
- **Auto Cleanup:** Expired OTPs are cleaned up on verification

**Functions:**
- `generate_otp()` - Generates 6-digit OTP
- `store_otp(email, user_id, purpose)` - Stores OTP with metadata
- `verify_otp(email, otp, purpose)` - Verifies OTP and returns user_id
- `delete_otp(email)` - Manually delete OTP
- `cleanup_expired_otps()` - Remove expired OTPs

### Email Templates

#### OTP Email (`send_otp_email`)
- Large, centered OTP code
- Purpose message ("recover your username" or "reset your password")
- 10-minute expiration warning
- Professional styling

#### Credentials Email (`send_credentials_email`)
- User ID
- Email address
- Temporary password (if password reset)
- Security warning to change password

### Pydantic Schemas (`app/schemas/employees.py`)
```python
class ForgotUsernameRequest(BaseModel):
    email: EmailStr

class ForgotPasswordOTPRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str
```

## Security Features

1. **Email Privacy:** Endpoints don't reveal if email exists in system
2. **Time-Limited OTPs:** 10-minute expiration
3. **Single-Use OTPs:** Deleted after successful verification
4. **Purpose Validation:** OTP must match intended purpose (username vs password)
5. **Temporary Password:** Random 12-character password for password reset
6. **Logging:** All operations logged for audit trail

## User Flow Examples

### Forgot Username
1. User clicks "Forgot Username"
2. User enters email → POST `/employees/forgot-username-otp`
3. User receives OTP via email (6 digits, expires in 10 minutes)
4. User enters OTP → POST `/employees/verify-otp-username`
5. User receives email with User ID
6. User can now login with User ID

### Forgot Password
1. User clicks "Forgot Password"
2. User enters email → POST `/employees/forgot-password-otp`
3. User receives OTP via email (6 digits, expires in 10 minutes)
4. User enters OTP → POST `/employees/verify-otp-password`
5. System generates temporary password and updates database
6. User receives email with User ID and temporary password
7. User can login with temporary password
8. **Important:** User should change password after first login

## Testing the Implementation

### Prerequisites
1. Ensure server is running with email credentials configured
2. Email service must be working (check SMTP configuration)

### Test Forgot Username
```bash
# Step 1: Request OTP
curl -X POST http://localhost:8000/employees/forgot-username-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# Step 2: Check email for OTP (6 digits)

# Step 3: Verify OTP
curl -X POST http://localhost:8000/employees/verify-otp-username \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "otp": "123456"}'

# Step 4: Check email for username
```

### Test Forgot Password
```bash
# Step 1: Request OTP
curl -X POST http://localhost:8000/employees/forgot-password-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# Step 2: Check email for OTP (6 digits)

# Step 3: Verify OTP
curl -X POST http://localhost:8000/employees/verify-otp-password \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "otp": "123456"}'

# Step 4: Check email for temporary password
# Step 5: Login with temporary password
```

## Production Considerations

### 1. OTP Storage
Current implementation uses in-memory storage. For production:
- **Redis:** Best for distributed systems
- **Database Table:** Create `otp_codes` table with expiry timestamps
- **Caching Layer:** Use application-level cache

Example Redis implementation:
```python
import redis
from datetime import timedelta

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def store_otp_redis(email: str, user_id: str, purpose: str) -> str:
    otp = generate_otp()
    key = f"otp:{email}:{purpose}"
    value = f"{user_id}:{otp}"
    redis_client.setex(key, timedelta(minutes=10), value)
    return otp
```

### 2. Rate Limiting
Implement rate limiting to prevent abuse:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/forgot-username-otp")
@limiter.limit("3/hour")  # 3 requests per hour per IP
async def forgot_username_otp(...):
    ...
```

### 3. Email Delivery
- Configure proper SMTP relay (SendGrid, AWS SES, etc.)
- Implement email queue for reliability
- Add retry logic for failed sends

### 4. Monitoring
- Track OTP generation rate
- Monitor failed OTP attempts
- Alert on suspicious patterns (multiple failed attempts)

### 5. Password Policy
- Enforce minimum password strength
- Add password history (prevent reuse)
- Require password change on first login with temporary password

## File Structure
```
app/
├── routes/
│   └── employees.py          # OTP endpoints added
├── schemas/
│   └── employees.py          # OTP request/response schemas
└── utils/
    ├── otp_service.py        # OTP generation and verification
    └── email_service.py      # OTP and credentials email templates
```

## Next Steps (Future Enhancements)

1. **Change Password Screen:** After login with temporary password
2. **OTP Resend:** Allow user to request new OTP if expired
3. **Multi-Factor Authentication:** Use OTP as second factor
4. **SMS OTP:** Alternative to email for OTP delivery
5. **Account Lockout:** After multiple failed OTP attempts
6. **Password Strength Meter:** Real-time validation
7. **Security Questions:** Additional recovery method

## Troubleshooting

### OTP Not Received
1. Check email service configuration (`SMTP_USER`, `SMTP_PASSWORD`)
2. Check spam/junk folder
3. Verify email address is correct
4. Check server logs for email errors

### OTP Invalid or Expired
1. OTPs expire after 10 minutes
2. OTPs are single-use (deleted after verification)
3. Purpose must match (username vs password)
4. Email must match exactly

### Email Not Sending Credentials
1. Ensure OTP verification succeeded
2. Check email service logs
3. Verify email template rendering
4. Check database password update (for password reset)

## Support
For issues or questions, check the server logs:
```bash
# View recent logs
tail -f logs/app.log

# Search for OTP-related logs
grep "OTP" logs/app.log
```
