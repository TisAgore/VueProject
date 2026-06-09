"""
Клиент Odoo 18.

Стандартный Odoo НЕ имеет REST-эндпоинтов /api/<model> — это сторонние модули.
Родной механизм — JSON-RPC:
  1. /web/session/authenticate         — сессионная аутентификация (логин/пароль)
  2. /web/dataset/call_kw              — вызов методов ORM (search_read, read, ...)

Мы используем:
  - /web/session/authenticate для проверки логина пользователя
  - Технический пользователь из .env (admin) для чтения проектов/задач через call_kw
"""

import re
import httpx
from fastapi import HTTPException
from config import get_settings
from schemas import OdooProject, OdooTask

settings = get_settings()

# Таймаут для всех запросов к Odoo
TIMEOUT = httpx.Timeout(15.0)


# ─────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────

def _strip_html(value) -> str:
    """Превращает Odoo Html-поле (или False) в чистый текст."""
    if not value or not isinstance(value, str):
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", text).strip()


async def _odoo_authenticate(login: str, password: str) -> dict:
    """
    POST /web/session/authenticate
    Возвращает словарь с uid, name, email (username) и session_id при успехе.
    Бросает HTTPException при неверных credentials.
    """
    url = f"{settings.odoo_url}/web/session/authenticate"
    payload = {
        "jsonrpc": "2.0",
        "method":  "call",
        "params": {
            "db":       settings.odoo_db,
            "login":    login,
            "password": password,
        },
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Odoo недоступен: {e}")

    data = resp.json()
    result = data.get("result", {})

    # Odoo возвращает uid=False при неверных данных
    if not result or not result.get("uid"):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль Odoo")

    return {
        "uid":      result["uid"],
        "name":     result.get("name", ""),
        "email":    result.get("username", login),
        "session":  resp.cookies.get("session_id", ""),
    }


async def _admin_session() -> str:
    """
    Аутентифицирует технического пользователя из .env и возвращает session_id.
    Используется для чтения проектов и задач от имени системы.
    """
    data = await _odoo_authenticate(
        settings.odoo_admin_login,
        settings.odoo_admin_password,
    )
    if not data["session"]:
        raise HTTPException(status_code=502, detail="Odoo не вернул session_id для admin")
    return data["session"]


async def _call_kw(
    session_id: str,
    model: str,
    method: str,
    args: list,
    kwargs: dict | None = None,
):
    """
    POST /web/dataset/call_kw — вызов метода ORM-модели Odoo.
    Например: model='project.project', method='search_read', args=[domain, fields].
    """
    url = f"{settings.odoo_url}/web/dataset/call_kw"
    payload = {
        "jsonrpc": "2.0",
        "method":  "call",
        "params": {
            "model":  model,
            "method": method,
            "args":   args,
            "kwargs": kwargs or {},
        },
    }
    async with httpx.AsyncClient(timeout=TIMEOUT, cookies={"session_id": session_id}) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Odoo API ошибка: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Odoo недоступен: {e}")

    data = resp.json()
    if "error" in data:
        msg = data["error"].get("data", {}).get("message") or data["error"].get("message", "")
        raise HTTPException(status_code=502, detail=f"Odoo RPC ошибка: {msg}")

    return data.get("result", [])


# ─────────────────────────────────────────────────────────────
# Публичные сервисные функции
# ─────────────────────────────────────────────────────────────

async def authenticate_user(login: str, password: str) -> dict:
    """
    Проверяет логин/пароль пользователя через Odoo.
    Возвращает {uid, name, email}.
    """
    return await _odoo_authenticate(login, password)


async def get_projects(limit: int = 50) -> list[OdooProject]:
    """
    Возвращает список проектов из Odoo (модель project.project).
    """
    if not settings.odoo_url:
        # Режим без Odoo: заглушка для разработки
        return [
            OdooProject(id=1, name="Demo Project (Odoo не подключён)", task_count=0),
        ]

    session_id = await _admin_session()
    records = await _call_kw(
        session_id,
        "project.project",
        "search_read",
        args=[[], ["name", "task_count"]],
        kwargs={"limit": limit, "order": "name"},
    )

    return [
        OdooProject(
            id=r["id"],
            name=r.get("name") or "",
            description="",
            task_count=r.get("task_count") or 0,
        )
        for r in records
    ]


async def get_tasks(project_id: int, limit: int = 100) -> list[OdooTask]:
    """
    Возвращает задачи конкретного проекта (модель project.task).
    """
    if not settings.odoo_url:
        return []

    session_id = await _admin_session()
    records = await _call_kw(
        session_id,
        "project.task",
        "search_read",
        args=[
            [["project_id", "=", project_id]],
            ["name", "description", "stage_id", "user_ids"],
        ],
        kwargs={"limit": limit},
    )

    # search_read возвращает user_ids как список id — резолвим имена одним запросом
    all_uids = sorted({uid for r in records for uid in (r.get("user_ids") or [])})
    uid_to_name: dict[int, str] = {}
    if all_uids:
        users = await _call_kw(
            session_id, "res.users", "read", args=[all_uids, ["name"]]
        )
        uid_to_name = {u["id"]: u.get("name", "") for u in users}

    tasks: list[OdooTask] = []
    for r in records:
        # stage_id приходит как [id, "Название"] либо False
        stage = ""
        if isinstance(r.get("stage_id"), list) and len(r["stage_id"]) == 2:
            stage = r["stage_id"][1]

        assigned = ", ".join(
            uid_to_name.get(uid, "") for uid in (r.get("user_ids") or [])
        ).strip(", ")

        tasks.append(
            OdooTask(
                id=r["id"],
                name=r.get("name") or "",
                description=_strip_html(r.get("description")),
                stage=stage,
                assigned_to=assigned,
            )
        )

    return tasks
