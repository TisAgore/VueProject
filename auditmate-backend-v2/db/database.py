from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency — выдаёт сессию и закрывает её после запроса."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Создаёт таблицы при первом запуске и применяет безопасные миграции."""
    from models import User, Chat, ChatMessage  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Миграция: добавляем поля панельного аудита (IF NOT EXISTS — идемпотентно)
        await conn.execute(text(
            "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS panel_id VARCHAR(36)"
        ))
        await conn.execute(text(
            "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS sub_role VARCHAR(50)"
        ))
        await conn.execute(text(
            "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS search_query VARCHAR(500)"
        ))
