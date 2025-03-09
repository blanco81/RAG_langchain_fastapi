import aiofiles
import os
from nanoid import generate
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from nanoid import generate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Importar modelos y schemas
from app.models import Document, User
from app.models.rag import History
from app.schemas.rag import DocumentResponse, HistoryResponse, QueryRequest

# Importar dependencias para la base de datos y autenticación
from app.core.deps import get_db
from app.core.dependencies import get_current_user

# Importar funciones del servicio RAG (basado en SentenceTransformers local)
from app.services.rag import (
    extract_text_from_pdf,
    process_query,
    store_embedding
)

router = APIRouter()

permission_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Permission denied"
)
internalServer_exception = HTTPException(
    status_code=500, 
    detail="Internal Server Error"
)


@router.post("/upload-document", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        if current_user.role not in ["Admin", "User"]:
            raise HTTPException(status_code=403, detail="No tiene permisos para realizar esta acción.")        
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="El archivo debe ser un PDF.")        
        content = await file.read()       
        
        temp_file_path = f"/tmp/{file.filename}"
        async with aiofiles.open(temp_file_path, "wb") as f:
            await f.write(content)
        
        text = await extract_text_from_pdf(temp_file_path)        
        doc_id = generate()        
        document = await store_embedding(db, doc_id, text, file.filename, current_user.id)        
        os.remove(temp_file_path)
        
        return document
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el documento: {str(e)}")

@router.post("/query", response_model=str)
async def query_documents(
    query_req: QueryRequest,  
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["Admin", "User"]:
        raise HTTPException(status_code=403, detail="No tiene permisos para realizar esta acción.")        

    query = query_req.query  
    response = await process_query(query, current_user.id, db)    
    
    return response

@router.get("/history", response_model=list[HistoryResponse])
async def get_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        if current_user.role not in ["Admin", "User"]:
            raise HTTPException(status_code=403, detail="No tiene permisos para realizar esta acción.") 
        
        result = await db.execute(
            select(History)
            .where(History.user_id == current_user.id)
            .order_by(History.created_at.desc())
            )
        histories = result.scalars().all()
        return histories
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener el historial: {str(e)}")



@router.get("/documents", response_model=list[DocumentResponse])
async def get_user_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        if current_user.role not in ["Admin", "User"]:
            raise HTTPException(status_code=403, detail="No tiene permisos para realizar esta acción.") 
        result = await db.execute(select(Document).where(Document.user_id == current_user.id))
        documents = result.scalars().all()
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener los documentos: {str(e)}")
