import pytz
from datetime import datetime
from nanoid import generate
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import Text
from app.core.database import Base
from app.core.config import settings


key = settings.DB_SECRET_KEY

class Logger(Base):
    __tablename__ = "logs"

    id = Column(String(40), primary_key=True, default=generate)
    action = Column(Text, nullable=False) 
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(pytz.utc))  
       
    user_id = Column(String(40), ForeignKey("users.id"))
    user = relationship("User", back_populates="logs", lazy="joined")
    