"""
Аутентификация: проксируем логин в Odoo, создаём/обновляем пользователя в нашей БД,
возвращаем JWT.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_db
from models import User
from schemas import LoginRequest, TokenResponse, CurrentUser
from services import odoo as odoo_svc
from services.auth import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    1. Проверяет логин/пароль через Odoo /web/session/authenticate
    2. Создаёт или обновляет пользователя в нашей PostgreSQL
    3. Возвращает JWT для последующих запросов
    """
    odoo_data = await odoo_svc.authenticate_user(body.login, body.password)
    odoo_uid  = odoo_data["uid"]
    name      = odoo_data["name"]
    email     = odoo_data["email"]

    result = await db.execute(select(User).where(User.odoo_uid == odoo_uid))
    user   = result.scalar_one_or_none()

    if user is None:
        user = User(odoo_uid=odoo_uid, email=email, name=name)
        db.add(user)
    else:
        user.name  = name
        user.email = email

    await db.commit()
    await db.refresh(user)

    token = create_access_token(user_id=user.id, odoo_uid=odoo_uid)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        odoo_uid=odoo_uid,
        name=name,
        email=email,
    )


@router.get("/me", response_model=CurrentUser)
async def me(current_user: CurrentUser = Depends(get_current_user)):
    """Возвращает данные текущего авторизованного пользователя."""
    return current_user
