# Email Unique Constraint Implementation

## Problem Statement
When multiple employees have the same email address in the database, the OTP-based forgot username/password recovery system cannot determine which user to recover, leading to:
- Ambiguous user identification
- Potential security issues
- Failed credential recovery

## Solution Implemented

### 1. Database Changes
**Made email column UNIQUE in employees table**

#### Model Update (`app/models/employees.py`)
```python
email = Column(String(100), unique=True, index=True, nullable=False)
```

#### Migration Script (`add_email_unique_constraint.py`)
- Checks for existing duplicate emails
- Optionally removes duplicates (keeps first occurrence)
- Adds UNIQUE constraint to email column
- Includes rollback functionality

### 2. Application-Level Validation
**Added email uniqueness checks in all registration endpoints**

#### Owner Registration (`/employees/register-owner`)
```python
# Check if email already exists
existing_employee = db.query(Employee).filter(Employee.email == owner_data.email).first()
if existing_employee:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Email address is already registered. Please use a different email or use the forgot password option."
    )
```

#### Employee Registration (`/employees/register`)
```python
# Check if email already exists
existing_employee = db.query(Employee).filter(Employee.email == employee.email).first()
if existing_employee:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Email address is already registered. Please use a different email."
    )
```

#### Employee Creation (`/employees/`)
Already had email uniqueness check:
```python
db_employee = db.query(Employee).filter(Employee.email == employee.email).first()
if db_employee:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Email already registered"
    )
```

## Migration Steps

### Step 1: Run Migration Script
```powershell
python add_email_unique_constraint.py
```

**What it does:**
1. Connects to the database
2. Checks for duplicate email addresses
3. If duplicates found:
   - Lists all duplicates
   - Asks if you want to remove them
   - Keeps only the first record for each email
4. Adds UNIQUE constraint to email column
5. Verifies the constraint was added

### Step 2: Restart Server
After running the migration, restart your FastAPI server:
```powershell
# Stop current server (Ctrl+C)
# Then restart
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Benefits

### 1. **Unique User Identification**
- Each user has a unique email address
- OTP recovery works correctly for all users
- No ambiguity in user identification

### 2. **Database Integrity**
- Email uniqueness enforced at database level
- Prevents duplicate registrations
- Data consistency maintained

### 3. **Security Improvements**
- Prevents email-based confusion attacks
- Clear user-to-email mapping
- Secure credential recovery

### 4. **Better User Experience**
- Clear error messages when email is already registered
- Guides users to use forgot password if account exists
- Reliable credential recovery

## Testing

### Test 1: Duplicate Email Prevention
```powershell
# Try to register with same email twice
curl -X POST http://localhost:8000/employees/register-owner `
  -H "Content-Type: application/json" `
  -d '{
    "name": "Test User 1",
    "email": "test@example.com",
    "phone_number": "1234567890",
    "password": "Test123!",
    "confirm_password": "Test123!"
  }'

# Try again with same email - should fail
curl -X POST http://localhost:8000/employees/register-owner `
  -H "Content-Type: application/json" `
  -d '{
    "name": "Test User 2",
    "email": "test@example.com",
    "phone_number": "9876543210",
    "password": "Test456!",
    "confirm_password": "Test456!"
  }'
```

**Expected Response (second request):**
```json
{
  "detail": "Email address is already registered. Please use a different email or use the forgot password option."
}
```

### Test 2: OTP Recovery with Unique Emails
```powershell
# Should work correctly now
curl -X POST http://localhost:8000/employees/forgot-username-otp `
  -H "Content-Type: application/json" `
  -d '{"email": "test@example.com"}'
```

**Expected:** OTP sent to the unique user with that email

## Handling Existing Duplicates

### Scenario 1: No Duplicates
Migration will proceed smoothly and add the constraint.

### Scenario 2: Duplicates Exist

#### Option 1: Automatic Removal (Recommended for Testing)
```
Found 2 duplicate email addresses:
  - test@example.com: 3 occurrences
  - admin@example.com: 2 occurrences

Do you want to:
1. Remove duplicates (keep only the first record)
2. Cancel and fix manually
Enter choice (1 or 2): 1
```

The script will:
- Keep the employee with the lowest `emp_id` (first registered)
- Delete other employees with same email
- Add the UNIQUE constraint

#### Option 2: Manual Fix (Recommended for Production)
```
Enter choice (1 or 2): 2
```

Then manually:
1. Export duplicate employee data
2. Contact users to confirm which accounts are valid
3. Merge or delete duplicate accounts
4. Update email addresses for accounts to keep
5. Re-run migration script

### Query to Find Duplicates
```sql
SELECT email, COUNT(*) as count, STRING_AGG(emp_id::text, ', ') as emp_ids
FROM employees
GROUP BY email
HAVING COUNT(*) > 1
ORDER BY count DESC;
```

## Rollback Procedure

If you need to remove the UNIQUE constraint:

### Using Migration Script
```powershell
python add_email_unique_constraint.py
# Choose option 2: Revert UNIQUE constraint
```

### Manual SQL
```sql
ALTER TABLE employees
DROP CONSTRAINT IF EXISTS employees_email_unique;
```

## Error Messages

### Registration with Duplicate Email
**Owner Registration:**
```json
{
  "detail": "Email address is already registered. Please use a different email or use the forgot password option."
}
```

**Employee Registration:**
```json
{
  "detail": "Email address is already registered. Please use a different email."
}
```

### Database-Level Constraint Violation
If constraint is bypassed and duplicate email reaches database:
```json
{
  "detail": "duplicate key value violates unique constraint \"employees_email_unique\""
}
```

## Impact on Existing Features

### ✅ No Breaking Changes
- Login: Still works with User ID + password
- Employee listing: No changes
- Business operations: No changes
- Profile updates: No changes

### ✅ Enhanced Features
- **OTP Recovery:** Now works reliably
- **Registration:** Prevents duplicate emails
- **User Management:** Clear one-to-one email mapping

### ⚠️ Changes Required
- **Email Updates:** Cannot change email to one already in use
- **Bulk Import:** Must validate unique emails before import

## Best Practices Going Forward

### 1. Email Validation
- Validate email format on frontend
- Check email uniqueness before form submission
- Provide clear error messages

### 2. User Onboarding
- Guide users to forgot password if email exists
- Suggest alternative emails
- Provide support contact for issues

### 3. Data Import
```python
# When importing employees, check for duplicates
def import_employees(employee_list):
    emails = set()
    duplicates = []
    
    for emp in employee_list:
        if emp['email'] in emails:
            duplicates.append(emp['email'])
        emails.add(emp['email'])
    
    if duplicates:
        raise ValueError(f"Duplicate emails found: {duplicates}")
    
    # Proceed with import
```

### 4. Profile Updates
When allowing email updates, check uniqueness:
```python
@router.put("/employees/{emp_id}")
def update_employee(emp_id: int, employee: EmployeeUpdate, db: Session):
    # Check if new email is already used by another employee
    if employee.email:
        existing = db.query(Employee).filter(
            Employee.email == employee.email,
            Employee.emp_id != emp_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Email is already used by another employee"
            )
```

## Summary

### Before Migration
- ❌ Multiple employees could have same email
- ❌ OTP recovery failed with duplicate emails
- ❌ Unclear user identification

### After Migration
- ✅ Each email is unique across all employees
- ✅ OTP recovery works reliably
- ✅ Clear user identification
- ✅ Better data integrity
- ✅ Improved security

## Next Steps

1. **Run Migration:** `python add_email_unique_constraint.py`
2. **Restart Server:** Apply model changes
3. **Test Registration:** Verify duplicate prevention
4. **Test OTP Recovery:** Confirm it works correctly
5. **Update Frontend:** Add email validation
6. **Document for Users:** Inform about unique email requirement
