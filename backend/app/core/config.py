from functools import lru_cache
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Divination API"
    app_env: str = "dev"
    app_debug: bool = True
    db_persistence_enabled: bool = True
    admin_username: str = "admin"
    admin_password: str = "change_me"
    admin_session_ttl_minutes: int = 720
    site_gate_enabled: bool = True
    site_gate_password: str = ""
    site_gate_cookie_secret: str = "change_me_site_gate_secret"
    site_gate_ttl_seconds: int = 604800
    site_gate_cookie_secure: bool = False
    user_token_secret: str = "change_me_user_token"
    user_password_aes_secret: str = "change_me_user_password_aes_secret"

    # Option 1: full SQLAlchemy URL (requires manual URL encoding for special chars in password).
    database_url: str | None = None

    # Option 2: split fields, password will be URL encoded automatically.
    db_host: str = "127.0.0.1"
    db_port: int = 32306
    db_user: str = "root"
    db_password: str = "root"
    db_name: str = "divination"
    db_charset: str = "utf8mb4"

    openai_base_url: str = "http://103.239.152.247:8022/v1"
    openai_model: str = "qwen3.5-27b-fp8"
    openai_api_key: str = ""
    llm_enabled: bool = False
    llm_timeout_seconds: int = 20
    llm_max_tokens: int = 700

    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        encoded_password = quote_plus(self.db_password)
        return (
            f"mysql+pymysql://{self.db_user}:{encoded_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset={self.db_charset}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
