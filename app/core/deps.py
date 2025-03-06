from contextvars import ContextVar
from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session
from contextlib import asynccontextmanager

session_context_var: ContextVar[Optional[AsyncSession]] = ContextVar("_session", default=None)

@asynccontextmanager
async def set_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as db:  
        yield db         

async def get_db():
    async with async_session() as session:
        yield session
