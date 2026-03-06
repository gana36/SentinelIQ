from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    secret_key: str = "dev-secret-change-me"
    mock_mode: bool = True
    environment: str = "development"
    access_token_expire_minutes: int = 60 * 24  # 1 day

    # Database
    database_url: str = "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentineliq"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AWS Bedrock
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    bedrock_nova_lite_model_id: str = "amazon.nova-lite-v1:0"
    bedrock_nova_sonic_model_id: str = "amazon.nova-sonic-v1:0"
    bedrock_embedding_model_id: str = "amazon.nova-multimodal-embedding-v1"

    # Data Sources
    newsapi_key: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "SentinelIQ/1.0"
    polygon_api_key: str = ""

    # ML
    anomaly_model_path: str = "models/isolation_forest.joblib"
    faiss_index_path: str = "models/faiss.index"
    faiss_metadata_path: str = "models/faiss_metadata.json"

    # Pipeline
    mock_event_interval_seconds: int = 30
    signal_queue_maxsize: int = 500

    # LangSmith observability
    langchain_api_key: str = ""          # LANGCHAIN_API_KEY in env
    langchain_tracing_v2: bool = False   # LANGCHAIN_TRACING_V2 in env
    langchain_project: str = "sentineliq"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
