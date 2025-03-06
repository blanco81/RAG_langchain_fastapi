import os
from sqlalchemy.engine.url import URL
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME")
    
    # DB CONNECTION CONFIG    
    DB_DRIVER: str ="postgresql+asyncpg"
    DB_HOST: str = os.getenv("DB_HOST")
    DB_PORT: int = int(os.getenv("DB_PORT"))  # Default para 3306 se não estiver definido
    DB_USER: str = os.getenv("DB_USER")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")
    DB_DATABASE: str = os.getenv("DB_DATABASE")

    # Outras configurações  
    ALGORITHM: str = os.getenv("ALGORITHM")  # Algoritmo de codificação JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))  # Default para 30 minutos se não definido
    DB_SECRET_KEY: str = os.getenv("DB_SECRET_KEY")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    
    QDRANT_URL: str = os.getenv("QDRANT_URL")
    
    # DB GENERAL CONFIG
    DB_POOL_SIZE: int = 15
    DB_MAX_OVERFLOW: int = 0
    DB_ECHO: bool = False
    

    @property
    def DB_DSN(self) -> URL:
        return URL.create(
            self.DB_DRIVER,
            self.DB_USER,
            self.DB_PASSWORD,
            self.DB_HOST,
            self.DB_PORT,
            self.DB_DATABASE,
        )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
print("----ENV DB Settings----")
print(f"DB_HOST: {settings.DB_HOST}")
print(f"DB_PORT: {settings.DB_PORT}")
