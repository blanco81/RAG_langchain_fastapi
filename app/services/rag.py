from datetime import datetime
import aiofiles
import io
import PyPDF2
import pytz
import uuid
from groq import Groq
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
from langchain.text_splitter import RecursiveCharacterTextSplitter

groq_api_key = settings.GROQ_API_KEY

if groq_api_key is None:
    raise ValueError("GROQ_API_KEY não está definido. Por favor, verifique o seu .env file.")

client = Groq(api_key=groq_api_key)

qdrant_client = QdrantClient(settings.QDRANT_URL)
COLLECTION_NAME = "documents"


def validate_or_generate_uuid(doc_id: str) -> str:
    try:
        return str(uuid.UUID(doc_id))
    except ValueError:
        return str(uuid.uuid4())

try:
    qdrant_client.get_collection(COLLECTION_NAME)
except:
    qdrant_client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={"size": 384, "distance": "Cosine"}  # Ajusta el tamaño según el modelo de embeddings
    )

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

memory = ConversationBufferMemory()

# ---------------------------
# Funciones de Memoria
# ---------------------------

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,  # Tamaño máximo de cada chunk (en caracteres)
    chunk_overlap=200,  # Solapamiento entre chunks (opcional)
    length_function=len,  # Función para calcular la longitud del texto
    separators=["\n\n", "\n", " ", ""]  # Separadores para dividir el texto
)

def split_text_into_chunks(text: str) -> List[str]:
    chunks = text_splitter.split_text(text)
    return chunks


async def summarize_memory(history: str) -> str:
    if not history:
        return ""

    prompt_summary = f"""
    Resuma la siguinte conversación de manera concisa, manteniendo el contexto principal:

    {history}

    Resumen:
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": prompt_summary}],
        max_tokens=100,  # Limitando o resumo a 100 tokens
        temperature=0.3
    )
    return response.choices[0].message.content.strip()




async def add_memory(user_id: str, user_input: str, bot_response: str, db: AsyncSession):    
    #summarized_history = await summarize_memory(bot_response)  # Resumo do histórico    
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
        .limit(5)
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
    filename: str, 
    user_id: str
):
    print(f"📥 Guardando documento en Qdrant - ID: {doc_id}")
    
    chunks = split_text_into_chunks(text_content)
    
    for i, chunk in enumerate(chunks):
        chunk_id = str(uuid.uuid4())
        
        embedding = embedding_model.encode(chunk).tolist()
        
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                PointStruct(
                    id=chunk_id,
                    vector=embedding,
                    payload={
                        "text": chunk,
                        "filename": filename,
                        "user_id": user_id,
                        "upload_date": str(datetime.now(pytz.utc)),
                        "chunk_index": i  
                    }
                )
            ]
        )        
        document = Document(
            id=chunk_id,
            filename=filename,
            vector_data=embedding,
            user_id=user_id,
            upload_date=datetime.now(pytz.utc)
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)
    
    db_log = Logger(
        action=f"Documento '{filename}' up-loaded en {len(chunks)} chunks.",
        created_at=datetime.now(pytz.utc),
        user_id=user_id
    )
    db.add(db_log)
    await db.commit()
    await db.refresh(db_log)
    
    print(f"✅ Documento guardado en Qdrant en {len(chunks)} chunks.")
    return document

# ---------------------------
# Consultar documentos más cercanos en base a embeddings
# ---------------------------
async def query_embedding(query_vector: List[float], top_k: int = 3):
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
    raw_history = await get_memory(user_id, db)  # Obtém histórico
    #summarized_history = await summarize_memory(raw_history)  # Resumo do histórico
    is_date_related_query = any(keyword in query.lower() for keyword in ["fecha", "cuándo", "día", "momento"])
   

    if is_date_related_query:
        prompt = f"""
        Eres un asistente de IA especializado en documentos. Usa la información a continuación para responder.        
                
        **Historial de conversación resumido:**
        {raw_history}
        
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

        prompt = f"""
        Eres un asistente de IA especializado en documentos. Usa la información a continuación para responder.
        
        **Historial de conversación resumido:**
        {raw_history}

        **Contexto relevante:**
        {context}

        **Pregunta:** {query}
        **Respuesta esperada:**
        """
        
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=600,
        temperature=0.5
    )

    assistant_response = response.choices[0].message.content.strip()

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

