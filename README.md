# Microservicio RAG con FastAPI, Qdrant y LangChain

Este microservicio implementa un sistema de Recuperación Aumentada Generativa (RAG) utilizando FastAPI, Qdrant para almacenamiento de vectores y LangChain para gestionar memoria conversacional. Procesa documentos en PDF y permite consultas basadas en embeddings.

## Tecnologías Utilizadas
- **FastAPI** para la API REST
- **SQLAlchemy** con PostgreSQL para metadatos
- **Qdrant** como base de datos vectorial
- **SentenceTransformers** para embeddings
- **LangChain** para memoria conversacional
- **llama-3.3-70b-versatile** para generación de respuestas
- **Groq** para ejecutar LLM

## Configuración
### Variables de Entorno
Debes definir las siguientes variables en `settings.py`:
```python
QDRANT_URL = "http://localhost:6333"
OPENAI_API_KEY = "tu_api_key"
```

## Endpoints Principales
### 1. Subir un Documento PDF y Almacenar su Embedding
**POST /upload-document**
- Extrae el texto del PDF y almacena el embedding en Qdrant y PostgreSQL.
- **Parámetros**: Archivo PDF, `user_id`
- **Respuesta**: Confirmación del almacenamiento.


### 2. Procesar una Consulta (RAG)
**POST /query**
- Integra el historial y los documentos para responder con OpenAI GPT-4o-mini.
- **Parámetros**: `query`, `user_id`
- **Respuesta**: Respuesta generada.

## Flujo de Datos
1. **Carga de PDF** → Se extrae el texto y se almacena el embedding en Qdrant.
2. **Consulta** → Se busca en Qdrant documentos similares y se combina con memoria conversacional.
3. **Generación de Respuesta** → Se usa OpenAI GPT-4o-mini con contexto relevante.

## Instalación y Ejecución
1. Instalar dependencias:
   ```sh
   pip install -r requirements.txt
   ```
2. Iniciar FastAPI:
   ```sh
   uvicorn app.main:app --reload
   ```
3. Acceder a la documentación interactiva en:
   ```
http://localhost:8000/docs```

