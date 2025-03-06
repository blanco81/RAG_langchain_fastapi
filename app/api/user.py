from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.user import (
    get_user, 
    get_users, 
    update_user, 
    deactivate_user, 
    activate_user
) 
from app.core.deps import get_db
from app.core.dependencies import get_current_user


router = APIRouter()

permission_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Permission denied"
    )

internalServer_exception = HTTPException(
        status_code=500, 
        detail="Internal Server Error"
    )

@router.get("/all", response_model=List[UserResponse])
async def read_users(    
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):    
    try:
        if current_user.role in ["Admin", "User"]:     
            users = await get_users(db, offset=offset, limit=limit)
            if not users:
                raise HTTPException(status_code=404, detail="Usuarios no encontrados")
            return users
        else:
            raise permission_exception
    except Exception as e:
        print(f"Error listing all users: {e}")
        raise internalServer_exception



@router.get("/show/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        if current_user.role in ["Admin"]:  
            user = await get_user(db, user_id)    
            if not user:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")
            return user
        else:
            raise permission_exception
    except Exception as e:
        print(f"Error showing user: {e}")
        raise internalServer_exception


@router.put("/edit/{user_id}", response_model=UserResponse)
async def edit_user(
    user_id: str,
    user: UserUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:        
        if current_user.role in ["Admin"]: 
            updated_user = await update_user(db, user_id, user)
            if not updated_user:
                raise HTTPException(status_code=404, detail="Usuario no Actualizado")
            return updated_user
        else:
            raise permission_exception
    except Exception as e:
        print(f"Error updating user: {e}")
        raise internalServer_exception
    

@router.delete("/deactivate/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    try:
        if current_user.role in ["Admin"]:       
            user_deleted = await deactivate_user(db, user_id) 
            if not user_deleted:                
                raise HTTPException(status_code=404, detail="Usuario no Desactivado")
            return JSONResponse(content={"status": "ok"}, status_code=status.HTTP_200_OK)
        else:
            raise permission_exception
    except Exception as e:
        print(f"Error deactivating user: {e}")
        raise internalServer_exception
    
@router.post("/activate/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def activat_user(
    user_id: str, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    try:
        if current_user.role in ["Admin"]:     
            user_activate = await activate_user(db, user_id)             
            if not user_activate:                
                raise HTTPException(status_code=404, detail="Usuario no Activado") 
            return JSONResponse(content={"status": "ok"}, status_code=status.HTTP_200_OK)
        else:
            raise permission_exception
    except Exception as e:
        print(f"Error activating user: {e}")
        raise internalServer_exception
    
    
@router.get("/filter")
async def filter_list_users(
    limit: int = Query(default=500, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if current_user.role in ["Admin", "User"]:
            result = await db.execute(select(User).where(User.active == True))
            all_users = result.scalars().all()

            users_dict = [{
                'id': user.id,
                'name_complete': user.name_complete,
                'email': user.email,
            } for user in all_users]

            if search:
                search_term = search.lower().strip()  # Convertir a minúsculas y eliminar espacios adicionales
                filtered_users = []
                
                for user in users_dict:
                    name_complete = user['name_complete'].lower()
                    email = user['email'].lower()
                                
                    # Calcular la puntuación de coincidencia
                    score = 0
                    # Puntuar si el término de búsqueda está en el nombre completo
                    if search_term in name_complete:
                        # Mayor puntuación si el término está al principio del nombre
                        if name_complete.startswith(search_term):
                            score += 100
                        else:
                            score += 50  # Puntuar menos si está en otra parte del nombre
                    # Puntuar si el término de búsqueda está en el email
                    if search_term in email:
                        # Mayor puntuación si el término está al principio del email
                        if email.startswith(search_term):
                            score += 100
                        else:
                            score += 50  # Puntuar menos si está en otra parte del email
                                
                    if score > 0:
                        user['score'] = score
                        filtered_users.append(user)
                
                # Ordenar los usuarios filtrados por puntuación (de mayor a menor) y luego por nombre completo
                filtered_users.sort(key=lambda x: (-x['score'], x['name_complete']))
            else:
                # Si no hay término de búsqueda, usar todos los usuarios
                filtered_users = users_dict
        
            # Aplicar paginación a los resultados ya filtrados
            total_users = len(filtered_users)
            paginated_users = filtered_users[offset:offset + limit]

            # Retornar el total de usuarios y los usuarios paginados
            return {
                "total": total_users,
                "users": paginated_users,
                "limit": limit,
                "offset": offset,
            }
        else:
            raise permission_exception
    except Exception as e:
        print(f"Error filtering users: {e}")
        raise internalServer_exception