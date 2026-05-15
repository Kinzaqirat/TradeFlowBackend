"""Authentication router: register, login, me."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
import bcrypt

# Monkeypatch bcrypt for passlib compatibility (fix for bcrypt >= 4.0.0)
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type('about', (object,), {'__version__': bcrypt.__version__})

from app.database import get_db
from app.models.user import User
from app.utils.jwt_handler import create_access_token
from app.dependencies import get_current_user
from app.schemas.auth import RegisterRequest, LoginRequest, AuthResponse, ProfileUpdateRequest

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user and return JWT token."""
    # Check uniqueness
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already taken")

    # Create user
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=pwd_context.hash(data.password),
    )
    db.add(user)
    await db.flush()

    token = create_access_token({"sub": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "email": user.email},
    }


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login and return JWT token."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "email": user.email},
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    return {"id": current_user.id, "username": current_user.username, "email": current_user.email}


@router.put("/profile")
async def update_profile(
    data: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update current user's profile information."""
    # Check if email is taken by another user
    if data.email != current_user.email:
        result = await db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already taken")

    # Check if username is taken by another user
    if data.username != current_user.username:
        result = await db.execute(select(User).where(User.username == data.username))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Username already taken")

    current_user.username = data.username
    current_user.email = data.email
    
    if data.password: # If password is provided, update it
        current_user.hashed_password = pwd_context.hash(data.password)

    await db.commit()
    await db.refresh(current_user)
    
    return {"id": current_user.id, "username": current_user.username, "email": current_user.email}
