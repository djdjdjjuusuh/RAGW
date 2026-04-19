from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    REDIS_URL: str = Field("redis://redis:6379/0", env="REDIS_URL")
    MILVUS_HOST: str = Field("milvus", env="MILVUS_HOST")
    MILVUS_PORT: int = Field(19530, env="MILVUS_PORT")
    MILVUS_COLLECTION: str = Field("doc_chunks", env="MILVUS_COLLECTION")
    OPENAI_API_KEY: str | None = Field(None, env="DEEPSEEK_API_KEY")
    OPENAI_MODEL: str = Field("deepseek-chat", env="OPENAI_MODEL")
    EMBEDDING_MODEL: str = Field("text-embedding-ada-002", env="EMBEDDING_MODEL")
    CHUNK_SIZE: int = Field(500, env="CHUNK_SIZE")
    MAX_HISTORY: int = Field(50, env="MAX_HISTORY")
    REDIS_TTL_SECONDS: int = Field(604800, env="REDIS_TTL_SECONDS")
    ALLOW_ORIGINS: str = Field("http://localhost:5173,http://localhost:4173,http://127.0.0.1:5173,http://127.0.0.1:4173", env="ALLOW_ORIGINS")
    UPLOAD_FOLDER: str = Field("uploads", env="UPLOAD_FOLDER")

    def allow_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOW_ORIGINS.split(",") if origin.strip()]


cfg = Settings()
