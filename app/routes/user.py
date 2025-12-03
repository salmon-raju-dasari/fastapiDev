from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, User as UserSchema, UserLogin, TokenWithRefresh, RefreshTokenRequest
from app.core.security import create_access_token, create_refresh_token, decode_token, is_refresh_token
from app.core.dependencies import get_current_user, require_role
from passlib.context import CryptContext

router = APIRouter()
logging.basicConfig(level=logging.INFO)

pwd_context = CryptContext(
    schemes=["argon2"],
    default="argon2",
    deprecated="auto",
)
# Password hashing configuration and verification
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        # Check if email already exists
        db_user = db.query(User).filter(User.email == user.email).first()
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if username already exists
        db_user = db.query(User).filter(User.username == user.username).first()
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Create new user
        try:
            logging.info(f"Attempting to hash password for user {user.username}")
            
            hashed_password = pwd_context.hash(user.password)
            logging.info(f"Successfully hashed password for user {user.username}")
            
            db_user = User(
                email=user.email,
                username=user.username,
                hashed_password=hashed_password,
                full_name=user.full_name,
                role=user.role
            )
        except Exception as e:
            logging.error(f"Error hashing password: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing password: {str(e)}"
            )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Return without the hashed password
        return UserSchema(
            id=db_user.id,
            email=db_user.email,
            username=db_user.username,
            full_name=db_user.full_name,
            role=db_user.role
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/", response_model=List[UserSchema])
def get_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all users - requires authentication"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.get("/{user_id}", response_model=UserSchema)
def get_user(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific user - requires authentication"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Delete a user - requires admin role"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(db_user)
    db.commit()
    # Return a confirmation JSON so clients receive a clear response
    return {"user_id": user_id, "detail": "deleted successfully"}

@router.put("/{user_id}", response_model=UserSchema)
def update_user(
    user_id: int,
    user_update: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a user - requires authentication. Users can only update themselves unless admin"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user is updating themselves or if they're an admin
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile"
        )
    
    # Check if email is being changed and if it's already taken
    if user_update.email != db_user.email:
        email_exists = db.query(User).filter(User.email == user_update.email).first()
        if email_exists:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if username is being changed and if it's already taken
    if user_update.username != db_user.username:
        username_exists = db.query(User).filter(User.username == user_update.username).first()
        if username_exists:
            raise HTTPException(status_code=400, detail="Username already taken")
    
    # Update user fields
    db_user.email = user_update.email
    db_user.username = user_update.username
    db_user.hashed_password = pwd_context.hash(user_update.password)
    db_user.full_name = user_update.full_name
    db_user.role = user_update.role
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/auth", response_model=TokenWithRefresh)
async def authenticate_user(userdetails: UserLogin, db: Session = Depends(get_db)):
    logging.info(f"Authenticating user with email: {userdetails.email}")
    db_user = db.query(User).filter(User.email == userdetails.email).first()
    if not db_user or not verify_password(userdetails.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Create JWT access token and refresh token
    access_token = create_access_token({"sub": str(db_user.id), "role": db_user.role})
    refresh_token = create_refresh_token({"sub": str(db_user.id), "role": db_user.role})
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}


@router.post("/refresh", response_model=TokenWithRefresh)
async def refresh_token(request: RefreshTokenRequest):
    # Validate refresh token
    if not is_refresh_token(request.refresh_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    payload = decode_token(request.refresh_token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    user_id = payload.get("sub")
    role = payload.get("role")

    access_token = create_access_token({"sub": str(user_id), "role": role})
    new_refresh = create_refresh_token({"sub": str(user_id), "role": role})
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": new_refresh}