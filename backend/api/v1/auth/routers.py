from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.schemas.auth import UserLogin, UserRegister, Token
from backend.dependencies.database import get_postgres_db

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/register", response_model=Token)
async def register(user_in: UserRegister, db: Session = Depends(get_postgres_db)):
    """Register a new user."""
    pass

@router.post("/login", response_model=Token)
async def login(user_in: UserLogin, db: Session = Depends(get_postgres_db)):
    """Authenticate and return JWT access and refresh tokens."""
    pass

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: Session = Depends(get_postgres_db)):
    """Exchange a valid refresh token for a new access token."""
    pass

@router.post("/logout")
async def logout(refresh_token: str, db: Session = Depends(get_postgres_db)):
    """Revoke the provided refresh token."""
    pass
    
@router.get("/oauth/{provider}")
async def oauth_login(provider: str):
    """Placeholder for OAuth (Spotify, Google) integration."""
    pass
