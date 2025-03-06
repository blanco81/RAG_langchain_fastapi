from jose import JWTError, jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.user import get_user_by_email
from app.models.user import User
from app.core.deps import get_db
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Extraer el token de las cookies
    token = request.cookies.get("access_token")
    if not token:
        print("No token found in cookies")
        raise credentials_exception

    try:
        # Decodificar el token (elimina el prefijo "Bearer")
        payload = jwt.decode(token.split(" ")[1], settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_email: str = payload.get("sub")
        if not user_email:
            print("No 'sub' field in payload")
            raise credentials_exception

        # Obtener el usuario de la base de datos
        user = await get_user_by_email(db, email=user_email)
        if not user:
            print(f"No user found with email: {user_email}")
            raise credentials_exception

    except JWTError as e:
        print(f"JWTError: {e}")
        raise credentials_exception

    return user