"""JWT-аутентификация: создание токена, проверка, dependency."""

from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import get_settings
from db.database import get_db
from models import User
from schemas import CurrentUser

settings = get_settings()
bearer   = HTTPBearer()


def create_access_token(user_id: int, odoo_uid: int) -> str:
    """Создаёт JWT токен."""
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub":      str(user_id),
        "odoo_uid": odoo_uid,
        "exp":      expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """
    FastAPI dependency — декодирует JWT и возвращает текущего пользователя.
    Используйте в роутах: current_user: CurrentUser = Depends(get_current_user)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Невалидный или просроченный токен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload  = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(user_id), User.is_active == True))
    user   = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    return CurrentUser(
        id=user.id,
        odoo_uid=user.odoo_uid,
        name=user.name,
        email=user.email,
    )
