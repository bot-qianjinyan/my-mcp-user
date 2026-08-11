from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "User API"
    secret_key: str = "dev-secret-change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    database_url: str = "sqlite:///./data/users.db"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 3001
    api_base_url: str = "http://127.0.0.1:8000"


settings = Settings()
