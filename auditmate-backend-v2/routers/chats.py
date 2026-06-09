"""
Чаты и сообщения — основная логика AuditMate.

Чат привязан к проекту Odoo (odoo_project_id).
При отправке сообщения:
  1. Сохраняем user-сообщение в БД
  2. Подтягиваем задачи проекта из Odoo для контекста
  3. Берём историю чата из БД (последние 20 сообщений)
  4. Отправляем в HuggingFace
  5. Сохраняем ответ ассистента в БД
  6. Возвращаем ответ
"""

import asyncio
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from db.database import get_db
from models import Chat, ChatMessage
from schemas import (
    ChatCreate, ChatUpdate, ChatOut, SendMessageRequest, MessageOut,
    PanelResponseOut, CurrentUser,
)
from services.auth import get_current_user
from services import odoo as odoo_svc
from services.ai import call_hf, call_hf_synthesis, PANEL_MAX_TOKENS

router = APIRouter(prefix="/chats", tags=["chats"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _chat_to_out(chat: Chat, message_count: int = 0) -> ChatOut:
    return ChatOut(
        id=chat.id,
        odoo_project_id=chat.odoo_project_id,
        project_name=chat.project_name,
        ai_role=chat.ai_role,
        title=chat.title,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        message_count=message_count,
    )


# ── Chats CRUD ────────────────────────────────────────────────────────────────

@router.get("", response_model=list[ChatOut])
async def list_chats(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Все чаты текущего пользователя (с кол-вом сообщений)."""
    result = await db.execute(
        select(Chat, func.count(ChatMessage.id).label("msg_count"))
        .outerjoin(ChatMessage, ChatMessage.chat_id == Chat.id)
        .where(Chat.user_id == current_user.id)
        .group_by(Chat.id)
        .order_by(Chat.updated_at.desc())
    )
    rows = result.all()
    return [_chat_to_out(chat, count) for chat, count in rows]


@router.post("", response_model=ChatOut, status_code=201)
async def create_chat(
    body: ChatCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Создаёт новый чат, привязанный к проекту Odoo."""
    chat = Chat(
        user_id=current_user.id,
        odoo_project_id=body.odoo_project_id,
        project_name=body.project_name,
        ai_role=body.ai_role,
        title=body.title,
    )
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    return _chat_to_out(chat, 0)


@router.get("/{chat_id}", response_model=ChatOut)
async def get_chat(
    chat_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Chat).where(Chat.id == chat_id, Chat.user_id == current_user.id))
    chat   = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    count_result = await db.execute(
        select(func.count(ChatMessage.id)).where(ChatMessage.chat_id == chat_id)
    )
    count = count_result.scalar_one()
    return _chat_to_out(chat, count)


@router.patch("/{chat_id}", response_model=ChatOut)
async def update_chat(
    chat_id: int,
    body: ChatUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Переименовать чат."""
    result = await db.execute(select(Chat).where(Chat.id == chat_id, Chat.user_id == current_user.id))
    chat   = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    chat.title = body.title
    await db.commit()
    await db.refresh(chat)
    count_result = await db.execute(
        select(func.count(ChatMessage.id)).where(ChatMessage.chat_id == chat_id)
    )
    return _chat_to_out(chat, count_result.scalar_one())


@router.delete("/{chat_id}", status_code=204)
async def delete_chat(
    chat_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Chat).where(Chat.id == chat_id, Chat.user_id == current_user.id))
    chat   = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    await db.delete(chat)
    await db.commit()


# ── Messages ──────────────────────────────────────────────────────────────────

@router.get("/{chat_id}/messages", response_model=list[MessageOut])
async def get_messages(
    chat_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """История сообщений чата."""
    # Проверяем, что чат принадлежит пользователю
    result = await db.execute(select(Chat).where(Chat.id == chat_id, Chat.user_id == current_user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Чат не найден")

    msgs = await db.execute(
        select(ChatMessage).where(ChatMessage.chat_id == chat_id).order_by(ChatMessage.created_at)
    )
    return [MessageOut.model_validate(m) for m in msgs.scalars().all()]


@router.post("/{chat_id}/messages", response_model=MessageOut)
async def send_message(
    chat_id: int,
    body: SendMessageRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Отправляет сообщение в чат:
    1. Сохраняет user-сообщение
    2. Строит контекст из задач Odoo
    3. Берёт историю из БД
    4. Вызывает HuggingFace
    5. Сохраняет и возвращает ответ ассистента
    """
    # Проверяем доступ к чату
    result = await db.execute(select(Chat).where(Chat.id == chat_id, Chat.user_id == current_user.id))
    chat   = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    # 1. Сохраняем user-сообщение
    user_msg = ChatMessage(chat_id=chat_id, role="user", content=body.content)
    db.add(user_msg)
    await db.commit()

    # 2. Контекст из Odoo: задачи проекта
    try:
        tasks = await odoo_svc.get_tasks(chat.odoo_project_id, limit=30)
        if tasks:
            task_lines = "\n".join(
                f"- [{t.stage}] {t.name}" + (f" → {t.assigned_to}" if t.assigned_to else "")
                for t in tasks
            )
            project_context = f"Проект: {chat.project_name}\nЗадачи:\n{task_lines}"
        else:
            project_context = f"Проект: {chat.project_name}"
    except Exception:
        project_context = f"Проект: {chat.project_name}"

    # 3. История сообщений из БД (последние 20, без только что добавленного)
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.chat_id == chat_id)
        .order_by(ChatMessage.created_at)
        .limit(20)
    )
    history = [
        {"role": m.role, "content": m.content}
        for m in history_result.scalars().all()
    ]

    # 4. Вызов HuggingFace
    try:
        reply, tokens, search_query = await call_hf(
            role=chat.ai_role,
            messages=history,
            project_context=project_context,
            query_hint=body.content,
            temperature=body.temperature,
        )
    except Exception as e:
        # Откатываем user-сообщение при ошибке AI
        await db.delete(user_msg)
        await db.commit()
        raise HTTPException(status_code=502, detail=f"AI недоступен: {e}")

    # 5. Сохраняем ответ ассистента
    from config import get_settings
    assistant_msg = ChatMessage(
        chat_id=chat_id,
        role="assistant",
        content=reply,
        model=get_settings().hf_model,
        tokens=tokens,
        search_query=search_query,
    )
    db.add(assistant_msg)

    chat.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(assistant_msg)

    return MessageOut.model_validate(assistant_msg)


# ── Panel Audit ───────────────────────────────────────────────────────────────

PANEL_ROLES = ["founder", "investor", "mentor", "critic"]


@router.post("/{chat_id}/panel", response_model=PanelResponseOut, status_code=201)
async def send_panel_message(
    chat_id: int,
    body: SendMessageRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Панельный аудит: один запрос → 4 роли параллельно → AI-синтез.
    Возвращает ответы всех ролей и итоговый отчёт.
    """
    # 1. Проверяем доступ
    result = await db.execute(select(Chat).where(Chat.id == chat_id, Chat.user_id == current_user.id))
    chat   = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    panel_id = str(uuid.uuid4())

    # 2. Сохраняем user-сообщение (с panel_id для группировки в истории)
    user_msg = ChatMessage(
        chat_id=chat_id, role="user", content=body.content, panel_id=panel_id,
    )
    db.add(user_msg)
    await db.commit()
    await db.refresh(user_msg)

    # 3. Контекст из Odoo
    try:
        tasks = await odoo_svc.get_tasks(chat.odoo_project_id, limit=30)
        if tasks:
            task_lines = "\n".join(
                f"- [{t.stage}] {t.name}" + (f" → {t.assigned_to}" if t.assigned_to else "")
                for t in tasks
            )
            project_context = f"Проект: {chat.project_name}\nЗадачи:\n{task_lines}"
        else:
            project_context = f"Проект: {chat.project_name}"
    except Exception:
        project_context = f"Проект: {chat.project_name}"

    # 4. История (без только что сохранённого user-сообщения)
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.chat_id == chat_id)
        .order_by(ChatMessage.created_at)
        .limit(20)
    )
    history = [
        {"role": m.role, "content": m.content}
        for m in history_result.scalars().all()
        if m.id != user_msg.id
    ]
    # Текущий вопрос добавляем последним — иначе роли отвечают «вслепую»
    panel_messages = history + [{"role": "user", "content": body.content}]

    # 5. Параллельный вызов 4 ролей
    try:
        raw_results = await asyncio.gather(*[
            call_hf(role, panel_messages, project_context, query_hint=body.content,
                    temperature=body.temperature, max_tokens=PANEL_MAX_TOKENS)
            for role in PANEL_ROLES
        ])
    except Exception as e:
        await db.delete(user_msg)
        await db.commit()
        raise HTTPException(status_code=502, detail=f"AI недоступен: {e}")

    role_results: dict[str, tuple] = dict(zip(PANEL_ROLES, raw_results))

    # 6. Синтез
    try:
        synthesis_reply, synthesis_tokens = await call_hf_synthesis(role_results, project_context)
    except Exception as e:
        import traceback, logging
        logging.error(f"[SYNTHESIS ERROR] {e}\n{traceback.format_exc()}")
        synthesis_reply, synthesis_tokens = f"Синтез недоступен: {e}", 0

    # 7. Сохраняем все 5 ответов с panel_id
    from config import get_settings
    model_name = get_settings().hf_model
    tokens_total = 0
    saved_roles: dict[str, ChatMessage] = {}

    for role_name, (reply, tokens, search_query) in role_results.items():
        msg = ChatMessage(
            chat_id=chat_id,
            role="assistant",
            content=reply,
            model=model_name,
            tokens=tokens,
            panel_id=panel_id,
            sub_role=role_name,
            search_query=search_query,
        )
        db.add(msg)
        saved_roles[role_name] = msg
        tokens_total += tokens

    synth_msg = ChatMessage(
        chat_id=chat_id,
        role="assistant",
        content=synthesis_reply,
        model=model_name,
        tokens=synthesis_tokens,
        panel_id=panel_id,
        sub_role="synthesis",
    )
    db.add(synth_msg)
    tokens_total += synthesis_tokens

    chat.updated_at = datetime.utcnow()
    await db.commit()

    for msg in saved_roles.values():
        await db.refresh(msg)
    await db.refresh(synth_msg)

    return PanelResponseOut(
        panel_id=panel_id,
        user_message=MessageOut.model_validate(user_msg),
        roles={name: MessageOut.model_validate(m) for name, m in saved_roles.items()},
        synthesis=MessageOut.model_validate(synth_msg),
        tokens_total=tokens_total,
    )
