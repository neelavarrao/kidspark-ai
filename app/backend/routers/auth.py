from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from typing import Optional
import os
import jwt

from app.backend.models.user import UserCreate, User, Token, TokenData
from app.backend.services.supabase_service import get_supabase_client

router = APIRouter(tags=["Authentication"])

# JWT Configuration
SECRET_KEY = "kidspark_secret_key"  # In production, use a secure environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

# Authentication functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except Exception:
        raise credentials_exception

    supabase = get_supabase_client()
    user_response = supabase.table("users").select("*").eq("email", token_data.email).execute()

    if user_response.data and len(user_response.data) > 0:
        user = User(
            id=user_response.data[0].get("id"),
            email=user_response.data[0].get("email"),
            name=user_response.data[0].get("name"),
            created_at=user_response.data[0].get("created_at")
        )
        return user
    else:
        raise credentials_exception

@router.post("/register", response_model=User)
async def register(user: UserCreate):
    supabase = get_supabase_client()

    # Check if user already exists
    existing_user = supabase.table("users").select("*").eq("email", user.email).execute()

    if existing_user.data and len(existing_user.data) > 0:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    user_data = {
        "email": user.email,
        "password": user.password,  # In production, hash this password
        "name": user.name,
        "created_at": datetime.utcnow().isoformat()
    }

    new_user = supabase.table("users").insert(user_data).execute()

    if new_user.data and len(new_user.data) > 0:
        return User(
            id=new_user.data[0].get("id"),
            email=new_user.data[0].get("email"),
            name=new_user.data[0].get("name"),
            created_at=new_user.data[0].get("created_at")
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to create user")

@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    supabase = get_supabase_client()

    # Check user credentials
    user_response = supabase.table("users").select("*").eq("email", form_data.username).execute()

    if not user_response.data or len(user_response.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = user_response.data[0]

    # In production, verify hashed password
    if user.get("password") != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.get("email")}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=User)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    return current_user