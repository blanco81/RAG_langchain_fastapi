from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.core.deps import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.logger import Logger
from app.schemas.logger import LoggerResponse


router = APIRouter()    
    
@router.get("/all", response_model=list[LoggerResponse])
async def list_logger(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role in ["Admin", "User"]:
        query = (
            select(Logger)
            .options(
                joinedload(Logger.user)
            )
        )
        result = await db.execute(query)
        loggers = result.unique().scalars().all()

        loggers_response = [
            LoggerResponse(
                id=logger.id,
                user_id=logger.user_id,
                action=logger.action,
                created_at=logger.created_at
            )
            for logger in loggers
        ]

        return loggers_response
    else:
        raise HTTPException(status_code=403, detail="No tienes permisos para acceder a este recurso")
