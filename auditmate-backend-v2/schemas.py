"""Pydantic-схемы для всех эндпоинтов."""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, EmailStr

RoleType = Literal["founder", "investor", "mentor", "critic", "marketer", "financier", "lawyer"]

# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    login: str = Field(..., description="Email или логин от Odoo")
    password: str = Field(..., min_length=1)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    odoo_uid: int
    name: str
    email: str

class CurrentUser(BaseModel):
    id: int
    odoo_uid: int
    name: str
    email: str

# ── Odoo ──────────────────────────────────────────────────────────────────────

class OdooProject(BaseModel):
    id: int
    name: str
    description: str = ""
    task_count: int = 0

class OdooTask(BaseModel):
    id: int
    name: str
    description: str = ""
    stage: str = ""
    assigned_to: str = ""

# ── Chats ─────────────────────────────────────────────────────────────────────

class ChatCreate(BaseModel):
    odoo_project_id: int
    project_name: str
    ai_role: RoleType = "founder"
    title: str = "Новый аудит"

class ChatUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)

class ChatOut(BaseModel):
    id: int
    odoo_project_id: int
    project_name: str
    ai_role: RoleType
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}

# ── Messages ──────────────────────────────────────────────────────────────────

class MessageItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)

class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    # None → температура берётся по роли (ROLE_TEMPERATURE); число 0..2 — пользовательское переопределение
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)

class MessageOut(BaseModel):
    id: int
    chat_id: int
    role: str
    content: str
    model: str
    tokens: int
    created_at: datetime
    panel_id: Optional[str] = None
    sub_role: Optional[str] = None
    search_query: Optional[str] = None

    model_config = {"from_attributes": True}


class PanelResponseOut(BaseModel):
    panel_id: str
    user_message: MessageOut
    roles: dict[str, MessageOut]   # "founder"|"investor"|"mentor"|"critic" → MessageOut
    synthesis: MessageOut
    tokens_total: int

# ── AI chat (stateless, old endpoint kept for compatibility) ──────────────────

class ChatRequest(BaseModel):
    role: RoleType = "founder"
    messages: list[MessageItem] = Field(..., min_length=1, max_length=20)

class ChatResponse(BaseModel):
    reply: str
    role: RoleType
    model: str
    total_tokens: int

# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    model: str
    hf_token_set: bool
    db_connected: bool
    odoo_url: str
