"""
SQLAlchemy ORM models.

Таблицы:
  users        — зеркало res.users из Odoo (одна строка = один Odoo-пользователь)
  chats        — сессия аудита, привязана к project.project из Odoo
  chat_messages — одно сообщение внутри чата
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Integer, String, Text, DateTime, ForeignKey, Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int]          = mapped_column(Integer, primary_key=True)
    odoo_uid: Mapped[int]    = mapped_column(Integer, unique=True, nullable=False, index=True)
    email: Mapped[str]       = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str]        = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool]  = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    chats: Mapped[list["Chat"]] = relationship("Chat", back_populates="user", cascade="all, delete-orphan")


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int]              = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int]         = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    odoo_project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    project_name: Mapped[str]    = mapped_column(String(255), nullable=False)
    ai_role: Mapped[str]         = mapped_column(String(50), default="founder")  # founder|investor|mentor|critic
    title: Mapped[str]           = mapped_column(String(255), default="Новый аудит")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"]                      = relationship("User", back_populates="chats")
    messages: Mapped[list["ChatMessage"]]     = relationship(
        "ChatMessage", back_populates="chat",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int]        = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int]   = mapped_column(ForeignKey("chats.id"), nullable=False, index=True)
    role: Mapped[str]      = mapped_column(String(20), nullable=False)   # "user" | "assistant"
    content: Mapped[str]   = mapped_column(Text, nullable=False)
    model: Mapped[str]     = mapped_column(String(100), default="")      # какая модель ответила
    tokens: Mapped[int]    = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    # Поля для панельного аудита (null у обычных сообщений)
    panel_id: Mapped[Optional[str]]  = mapped_column(String(36), nullable=True, index=True)
    sub_role: Mapped[Optional[str]]  = mapped_column(String(50),  nullable=True)
    # Поисковый запрос, если ответ опирался на веб-поиск (null — поиска не было)
    search_query: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")
