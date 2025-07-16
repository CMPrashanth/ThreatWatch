import os
from datetime import datetime, timedelta
from typing import Optional
import logging # Import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from . import crud, models, security
from .database import get_db
from .config import settings

logger = logging.getLogger(__name__) # Get logger instance

# --- JWT and OAuth2 Configuration ---

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

SECRET_KEY = os.getenv("SECRET_KEY", "a_very_secret_key_for_development_only")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    """
    Authenticates a user by checking their username and password.
    """
    logger.info(f"Attempting to authenticate user: {username}")
    
    logger.info("Step 1: Fetching user from database...")
    user = crud.get_user_by_username(db, username=username)
    if not user:
        logger.warning(f"User '{username}' not found in database.")
        return None
    logger.info(f"User '{username}' found.")

    logger.info("Step 2: Verifying password...")
    if not security.verify_password(password, user.hashed_password):
        logger.warning(f"Password verification failed for user '{username}'.")
        return None
    logger.info(f"Password for '{username}' verified successfully.")
    
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a new JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    """
    FastAPI dependency to get the current user from a JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        token_data = models.TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception

    user = crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    A further dependency to ensure the user is active.
    """
    return current_user


async def get_current_admin_user(current_user: models.User = Depends(get_current_active_user)) -> models.User:
    """
    Dependency to ensure the user is an administrator.
    """
    if current_user.role != models.UserRoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges"
        )
    return current_user

