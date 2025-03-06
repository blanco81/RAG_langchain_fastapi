from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

load_dotenv()

engine = create_async_engine(
    settings.DB_DSN,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    future=True,
)

async_session = sessionmaker(
    engine,
    expire_on_commit=False, 
    class_=AsyncSession, 
    future=True
)

metadata = MetaData()
Base = declarative_base(metadata=metadata)


