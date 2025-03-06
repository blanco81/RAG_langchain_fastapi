from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from app.core.database import async_session
from app.api.auth import router as auth_router
from app.api.user import router as user_router
from app.api.core import router as logger_router
from app.api.rag import router as rag_router

from app.services.user import get_user_by_email, create_user, get_user_by_email
from app.schemas.user import UserCreate
from app.core.config import settings

class AuthRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            response = await call_next(request)
            if response.status_code == status.HTTP_401_UNAUTHORIZED:
                return RedirectResponse(url="/api/v1/auth/login")  
            return response
        except HTTPException as ex:
            if ex.status_code == status.HTTP_401_UNAUTHORIZED:
                return RedirectResponse(url="/api/v1/auth/login")  
            raise ex


def get_app() -> FastAPI:
    _app = FastAPI(
        title="RAG System",
    )
    
    _app.include_router(auth_router, prefix="/api/v1/auth", tags=["Autentication"])
    _app.include_router(user_router, prefix="/api/v1/users", tags=["Users"])
    _app.include_router(logger_router, prefix="/api/v1/loggers", tags=["Logs"])
    _app.include_router(rag_router, prefix="/api/v1/rags", tags=["RAGs"])

    _app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    _app.add_middleware(AuthRedirectMiddleware)
    
    _app.add_middleware(SessionMiddleware, secret_key=settings.DB_SECRET_KEY)

    return _app

app = get_app()


@app.on_event("startup")
async def on_startup():
    async with async_session() as db:
        admin_email = "admin@ragsys.com"
        if not await get_user_by_email(db, admin_email):
            admin_user = UserCreate(
                name_complete="admin",
                email=admin_email,
                password="admin",
                role="Admin"
            )
            await create_user(db, admin_user)  
             
    
            
@app.on_event("shutdown")
async def shutdown():
    await async_session.close_all()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)