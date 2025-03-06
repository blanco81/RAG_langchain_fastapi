import pytz
from datetime import datetime
from nanoid import generate
from sqlalchemy import Boolean, Column, String, DateTime
from sqlalchemy_utils import StringEncryptedType
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.config import settings


key = settings.DB_SECRET_KEY

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(40), primary_key=True, default=generate)
    name_complete = Column(StringEncryptedType(String(200), key), nullable=False)
    email = Column(StringEncryptedType(String(200), key), unique=True, index=True, nullable=False)
    password = Column(StringEncryptedType(String(200), key), nullable=False)
    role = Column(String(100), nullable=False) #Admin, User
    active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.utc), onupdate=lambda: datetime.now(pytz.utc))
    
    logs = relationship("Logger", back_populates="user")
    documents = relationship("Document", back_populates="user")
    histories = relationship("History", back_populates="user")
    