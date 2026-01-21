from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHROMA_BASE_DIR: str = "./chroma_db"  # Base directory for all ChromaDB files
    CHUNK_SIZE: int = 1500
    CHUNK_OVERLAP: int = 150
    RETRIEVER_K: int = 5
    MAX_TOKENS: int = 4000
    DB_CLEANUP_HOURS: int = 1  # Auto-delete DB files after 1 hour
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()