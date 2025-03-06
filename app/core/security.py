from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import pytz
from app.core.config import settings

key = settings.DB_SECRET_KEY

SECRET_KEY = settings.JWT_SECRET_KEY

ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:    
    to_encode = data.copy()    
    if expires_delta:
        expire = datetime.now(pytz.utc) + expires_delta
    else:
        expire = datetime.now(pytz.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)    
    return encoded_jwt


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        return payload
    except JWTError:
        return None
