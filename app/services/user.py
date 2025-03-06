from datetime import datetime
from fastapi import Query
import pytz
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.logger import Logger
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from typing import List, Optional

async def get_user(db: AsyncSession, usuario_id: str) -> User:    
    result = await db.execute(select(User).where(User.id == usuario_id, User.active == True))
    usuario = result.scalars().first()      
    return usuario

async def get_user_by_email(db: AsyncSession, email: str) -> User:
    result = await db.execute(select(User).where(User.email == email, User.active == True))
    usuario = result.scalars().first()        
    return usuario

async def get_users(db: AsyncSession, offset: int, limit: int) -> List[User]:
    query = select(User).where(User.active == True).offset(offset).limit(limit)    
    result = await db.execute(query)        
    users = result.scalars().all() 
    return users 

async def get_users_by_role(db: AsyncSession) -> List[User]:
    query = (
        select(User)
        .where(
            User.active == True,
            User.role.in_(["Admin", "User"])
        )
    )
    result = await db.execute(query)        
    usuarios = result.scalars().all()  
    return usuarios  

async def get_user_deactivate(db: AsyncSession, user_id: str) -> User:    
    result = await db.execute(select(User).where(User.id == user_id, User.active == False))
    user = result.scalars().first()      
    return user

async def create_user(db: AsyncSession, usuario: UserCreate) -> User:     
    user_data = usuario.dict(exclude_unset=True)     
    user_data["active"] = True      
    db_user = User(**user_data)      
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    db_log = Logger(
        action=f"User '{db_user.name_complete}' registered.",
        created_at=datetime.now(pytz.utc),
        user_id=db_user.id
    )
    db.add(db_log)
    await db.commit()
    await db.refresh(db_log)
    
    return db_user

async def update_user(db: AsyncSession, usuario_id: str, usuario_data: UserUpdate):
    db_user = await get_user(db, usuario_id)
    if db_user:
        for field, value in usuario_data.dict(exclude_unset=True).items():
            setattr(db_user, field, value)        
        await db.commit() 
        await db.refresh(db_user) 
        
    db_log = Logger(
        action=f"User '{db_user.name_complete}' updated.",
        created_at=datetime.now(pytz.utc),
        user_id=db_user.id
    )
    db.add(db_log)
    await db.commit()
    await db.refresh(db_log)
        
    return db_user

async def deactivate_user(db: AsyncSession, usuario_id: str) -> bool:
    db_user = await get_user(db, usuario_id)
    if not db_user:
        return False  
    db_user.active = 0  
    await db.commit()
    await db.refresh(db_user)
    
    db_log = Logger(
        action=f"User '{db_user.name_complete}' deactivated.",
        created_at=datetime.now(pytz.utc),
        user_id=db_user.id
    )
    db.add(db_log)
    await db.commit()
    await db.refresh(db_log)
        
    return True 

async def activate_user(db: AsyncSession, user_id: str) -> bool:
    db_user = await get_user_deactivate(db, user_id)
    if not db_user:
        return False  
    db_user.active = True  
    await db.commit()
    await db.refresh(db_user)
    
    db_log = Logger(
        action=f"User '{db_user.name_complete}' activated.",
        created_at=datetime.now(pytz.utc),
        user_id=db_user.id
    )
    db.add(db_log)
    await db.commit()
    await db.refresh(db_log)
    
    return True 

async def filter_users(   
    db: AsyncSession,
    limit: int = Query(default=500, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None)        
) -> List[User]:
    
    result = await db.execute(select(User).where(User.active == True))
    all_users = result.scalars().all()

    users_dict = [{
        'id': user.id,
        'name_complete': user.name_complete,
        'email': user.email,
    } for user in all_users]
    
    if search:
        search_term = search.lower().strip()  
        filtered_users = []
        
        for user in users_dict:
            name_complete = user['name_complete'].lower()
            email = user['email'].lower()
                        
            # Calcular la puntuación de coincidencia
            score = 0
            # Puntuar si el término de búsqueda es un prefijo del nombre completo
            if name_complete.startswith(search_term):
                score += 100  # Máxima prioridad para prefijos del nombre completo
            # Puntuar si el término de búsqueda es un prefijo del first_name o last_name
            if email.startswith(search_term):
                score += 50  # Prioridad media para prefijos de first_name o last_name
                        
            if score > 0:
                user['score'] = score
                filtered_users.append(user)
        
        # Ordenar los clientes filtrados por puntuación (de mayor a menor) y luego por nombre completo
        filtered_users.sort(key=lambda x: (-x['score'], x['name_complete']))
        users_dict = filtered_users
    
        # Aplicar paginación a los resultados ya filtrados
        total_users = len(users_dict)
        paginated_users = users_dict[offset:offset + limit]

        # Retornar el total de clientes y los clientes paginados
        return {
            "total": total_users,
            "users": paginated_users,
            "limit": limit,
            "offset": offset,
        }
        
    
    