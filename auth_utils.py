from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from database import get_db
from models import User
from schemas import Token

load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False) 
# auto_error=False means: "If no token, don't crash, just pass None"
# --- CONFIGURATION ---
# In a real app, put these in your .env file!
SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_kiraka_key_12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 Hours

# Password Hashing Tool
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# This tells FastAPI: "Look for the token in the 'Authorization: Bearer' header"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# --- 1. PASSWORD HELPERS ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# --- 2. TOKEN HELPERS ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- 3. THE "CURRENT USER" DEPENDENCY ---
# This is the most important function. It protects your routes.
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # New check: If token is None (because auto_error=False), raise error immediately
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception

    return user


async def get_current_user_optional(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None

    user = db.query(User).filter(User.email == email).first()
    return user