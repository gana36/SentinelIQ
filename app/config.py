import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

_env_file = os.environ.get("ENV_FILE", ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_env_file, env_file_encoding="utf-8", extra="ignore")

    # App
    secret_key: str = "dev-secret-change-me"
    mock_mode: bool = True
    environment: str = "development"
    access_token_expire_minutes: int = 60 * 24  # 1 day
    app_base_url: str = "http://localhost:8000"  # used for email confirm links
    frontend_url: str = "http://localhost:5173"  # React app URL for email deep links

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
    bedrock_embedding_model_id: str = "amazon.nova-2-multimodal-embeddings-v1:0"

    # Data Sources
    newsapi_key: str = ""
    finlight_api_key: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "SentinelIQ/1.0"
    polygon_api_key: str = ""
    twitter_bearer_token: str = ""  # Twitter API v2 Bearer token for cashtag search

    # ML
    anomaly_model_path: str = "models/isolation_forest.joblib"
    faiss_index_path: str = "models/faiss.index"
    faiss_metadata_path: str = "models/faiss_metadata.json"

    # Pipeline
    mock_event_interval_seconds: int = 30
    signal_queue_maxsize: int = 500

    # Demo mode — speeds up all polling intervals for live demos/videos
    # Set DEMO_MODE=true in .env.demo; leave false for deployed/production
    demo_mode: bool = False
    demo_mock_event_interval_seconds: int = 5   # mock events every 5s (vs 30s)
    demo_news_poll_interval_seconds: int = 30   # news every 30s (vs 300s)
    demo_twitter_poll_interval_seconds: int = 60  # twitter every 60s (vs 1800s)

    # Nova Act + Alpaca
    nova_act_headless: bool = True  # set False locally to show browser during demo
    nova_act_api_key: str = ""
    alpaca_email: str = ""
    alpaca_password: str = ""
    alpaca_api_key: str = ""
    alpaca_api_secret: str = ""

    # Email behaviour
    auto_email_alerts: bool = False   # set True to email on every alert automatically

    # Email (SMTP)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # LangSmith observability
    langchain_api_key: str = ""          # LANGCHAIN_API_KEY in env
    langchain_tracing_v2: bool = False   # LANGCHAIN_TRACING_V2 in env
    langchain_project: str = "sentineliq"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
