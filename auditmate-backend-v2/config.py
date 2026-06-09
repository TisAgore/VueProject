from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # HuggingFace
    hf_token: str = ""
    hf_model: str = "openai/gpt-oss-120b"

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://auditmate:secret@localhost:5432/auditmate"

    # JWT
    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # Odoo
    odoo_url: str = ""
    odoo_db: str = ""
    odoo_admin_login: str = ""
    odoo_admin_password: str = ""

    # Server
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
