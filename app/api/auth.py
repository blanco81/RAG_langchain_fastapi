from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import AccessToken, LoginRequest, UserCreate, UserResponse
from app.services.user import get_user_by_email, create_user
from app.core.security import create_access_token
from app.core.deps import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings

router = APIRouter()

@router.post("/login", response_model=AccessToken)
async def login(
    response: Response,  
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    db_user = await get_user_by_email(db, login_data.email)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not db_user.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    if not login_data.password == db_user.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": db_user.email, "role": str(db_user.role)})

    response.set_cookie(
        key="access_token", 
        value=f"Bearer {access_token}",  
        httponly=True, 
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  
        secure=False,  # Cambia a True en producción si usas HTTPS
        samesite="lax",  # Previene ataques CSRF
    )

    return AccessToken(access_token=access_token, token_type="Bearer")


@router.post("/register", response_model=UserResponse)
async def register(
    user: UserCreate,
    db: AsyncSession = Depends(get_db)
):   
    try:
        existing_user = await get_user_by_email(db, user.email)
        if existing_user:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Email is registered."}
            )        
        new_user = UserCreate(
            name_complete=user.name_complete, 
            email=user.email, 
            password=user.password, 
            role=user.role,
            active=True)   
             
        new_user = await create_user(db, new_user)         
        if not new_user:
            raise HTTPException(status_code=404, detail="User not registered")
        return new_user 
    except Exception as e:
        print(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    
@router.get("/me", response_model=UserResponse)
async def get_current_user_data(   
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user),
):
    try:
        return UserResponse(
            id=current_user.id,
            name_complete=current_user.name_complete,
            email=current_user.email,
            role=current_user.role,
            active=current_user.active,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at,
        )
    except Exception as e:
        print(f"Error fetching current user: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

@router.get("/logout")
async def logout():
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "exit"}
    )
    response.delete_cookie(key="access_token")
    return response