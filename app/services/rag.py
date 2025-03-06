from datetime import datetime
import aiofiles
import io
import PyPDF2
import openai
import pytz
import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from app.core.config import settings
from app.models.logger import Logger
from app.models.rag import Document, History
from langchain.memory import ConversationBufferMemory


def validate_or_generate_uuid(doc_id: str) -> str:
    try:
        return str(uuid.UUID(doc_id))
    except ValueError:
        return str(uuid.uuid4())

qdrant_client = QdrantClient(settings.QDRANT_URL)
COLLECTION_NAME = "documents"

try:
    qdrant_client.get_collection(COLLECTION_NAME)
except:
    qdrant_client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={"size": 384, "distance": "Cosine"}  # Ajusta el tamaño según el modelo de embeddings
    )

# --- Cargar modelo de embeddings ---
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Memoria de conversación de LangChain
memory = ConversationBufferMemory()

# ---------------------------
# Funciones de Memoria
# ---------------------------
async def add_memory(user_id: str, user_input: str, bot_response: str, db: AsyncSession):
    history_entry = History(
        query_text=user_input,
        response_text=bot_response,
        user_id=user_id
    )
    db.add(history_entry)
    await db.commit()

async def get_memory(user_id: str, db: AsyncSession) -> str:
    stmt = (
        select(History.query_text, History.response_text, History.created_at)
        .where(History.user_id == user_id)
        .order_by(History.created_at.desc())
        .limit(10)
    )
    result = await db.execute(stmt)
    history_data = result.fetchall()

    conversation_history = ""
    for query_text, response_text, created_at in history_data:
        conversation_history += f"- **Fecha:** {created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        conversation_history += f"  **Pregunta:** {query_text}\n"
        conversation_history += f"  **Respuesta:** {response_text}\n\n"

    return conversation_history.strip()

# ---------------------------
# Extraer texto de PDF de forma asíncrona
# ---------------------------
async def extract_text_from_pdf(file_path: str) -> str:   
    text = ""
    async with aiofiles.open(file_path, "rb") as file:
        content = await file.read()
    reader = PyPDF2.PdfReader(io.BytesIO(content))
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + " "
    return text.strip()

# ---------------------------
# Función para almacenar embeddings en Qdrant
# ---------------------------
async def store_embedding(
    db: AsyncSession, 
    doc_id: str, 
    text_content: str, 
    content_hash: str, 
    filename: str, 
    user_id: str
    ):
    print(f"📥 Guardando documento en Qdrant - ID: {doc_id}")
    
    valid_id = validate_or_generate_uuid(doc_id)

    embedding = embedding_model.encode(text_content).tolist()
    
    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=valid_id,
                vector=embedding,
                payload={"text": text_content, "filename": filename, "user_id": user_id, "upload_date": str(datetime.now(pytz.utc))}
            )
        ]
    )
    
    document = Document(
            id=doc_id,
            filename=filename,
            content_hash=content_hash,
            vector_data=embedding,
            user_id=user_id,
            upload_date=datetime.now(pytz.utc)
        )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    
    db_log = Logger(
        action=f"Documento '{filename}' up-loaded.",
        created_at=datetime.now(pytz.utc),
        user_id=user_id
    )
    db.add(db_log)
    await db.commit()
    await db.refresh(db_log)
    
    print(f"✅ Documento guardado en Qdrant con ID: {doc_id}")
    return document

# ---------------------------
# Consultar documentos más cercanos en base a embeddings
# ---------------------------
async def query_embedding(query_vector: List[float], top_k: int = 5):
    print(f"🔍 Consultando documentos similares en Qdrant")
    
    search_results = qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k
    )
    
    if not search_results:
        print("⚠️ No hay documentos en Qdrant.")
        return {"documents": []}
    
    documents = [hit.payload["text"] for hit in search_results if "text" in hit.payload]
    print("🔍 Documentos recuperados:", documents)
    return {"documents": documents}

# ---------------------------
# Procesar consulta (RAG)
# ---------------------------
async def process_query(query: str, user_id: str, db: AsyncSession) -> str:
    conversation_history = await get_memory(user_id, db)

    is_date_related_query = any(keyword in query.lower() for keyword in ["fecha", "cuándo", "día", "momento"])

    if is_date_related_query:
        prompt = f"""
        Actúa como un asistente de inteligencia artificial especializado en análisis de documentos. 
        Utiliza el siguiente historial de conversaciones para responder con precisión a la pregunta del usuario.
        Utiliza un tono asequible, cordial y viable a la hora de responderle al usuario.
        
                
        **Historial de conversación:**
        {conversation_history}
        
        **Instrucción adicional:**
        - Si la pregunta está relacionada con fechas, responde indicando la fecha exacta en que se realizó la pregunta.
        - La fecha está en el formato: YYYY-MM-DD HH:MM:SS.

        **Pregunta:** {query}
        **Respuesta esperada:**
        """
    else:
        query_embedding_vector = embedding_model.encode(query).tolist()
        results = await query_embedding(query_embedding_vector)
        context = " ".join(results["documents"]) or "Sin contexto adicional."

        print("📄 Contexto recuperado:", context)

        prompt = f"""
        Actúa como un asistente de inteligencia artificial especializado en análisis de documentos. 
        Utiliza la siguiente información para responder con precisión a la pregunta del usuario.
        Utiliza un tono asequible, cordial y viable a la hora de responderle al usuario.
        
        **Historial de conversación:**
        {conversation_history}

        **Contexto relevante:**
        {context}

        **Pregunta:** {query}
        **Respuesta esperada:**
        """

    openai.api_key = settings.OPENAI_API_KEY
    
    response = await openai.ChatCompletion.acreate(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=200,
        temperature=0.6
    )

    assistant_response = response["choices"][0]["message"]["content"].strip()

    await add_memory(user_id, query, assistant_response, db)
    
    db_log = Logger(
        action=f"Query '{query}' up-loaded.",
        created_at=datetime.now(pytz.utc),
        user_id=user_id
    )
    db.add(db_log)
    await db.commit()
    await db.refresh(db_log)

    return assistant_response

