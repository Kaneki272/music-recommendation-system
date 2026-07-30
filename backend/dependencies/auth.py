from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from backend.security.jwt import SECRET_KEY, ALGORITHM
from backend.schemas.auth import TokenPayload
from backend.dependencies.database import get_postgres_db
from backend.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    db: Session = Depends(get_postgres_db), 
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenPayload(**payload)
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.id == token_data.sub).first()
    if user is None:
        raise credentials_exception
    return user

def require_permission(required_permission: str):
    async def permission_checker(current_user: User = Depends(get_current_user)):
        # Placeholder for RBAC permission checking logic
        # Will join User -> UserRole -> Role -> RolePermission -> Permission
        has_permission = True 
        if not has_permission:
            raise HTTPException(status_code=403, detail="Not enough privileges")
        return current_user
    return permission_checker
