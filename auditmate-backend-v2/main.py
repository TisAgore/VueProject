"""
AuditMate — FastAPI бэкенд
HuggingFace Inference + Odoo 18 REST API + PostgreSQL
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from pathlib import Path

from config import get_settings
from db.database import init_db, get_db
from routers.auth  import router as auth_router
from routers.odoo  import router as odoo_router
from routers.chats import router as chats_router
from schemas import ChatRequest, ChatResponse, HealthResponse
from services.ai import call_hf

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="AuditMate API",
    description="Умный аудит стартапа · FastAPI + HuggingFace + Odoo 18 + PostgreSQL",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(odoo_router)
app.include_router(chats_router)

# Статика — Vue сборка (dist/ скопированный в static/)
static_dir = Path("static")
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")


@app.get("/", include_in_schema=False)
async def root():
    index = Path("static/index.html")
    if index.exists():
        return FileResponse(index)
    return {"message": "AuditMate API v2.0 · /docs для Swagger"}


# SPA-fallback: любые НЕ-API GET-маршруты (например /login, /dashboard)
# отдают index.html, чтобы Vue Router работал при прямом заходе по ссылке.
# Реализовано через обработчик 404, а НЕ catch-all роут — иначе catch-all
# создаёт "partial match" и ломает 405/redirect-slashes для /api-методов
# (из-за этого POST /chats отдавал 405 Method Not Allowed).
_API_PREFIXES = (
    "/auth", "/odoo", "/chats", "/chat", "/health", "/roles",
    "/docs", "/redoc", "/openapi.json", "/assets",
)


@app.exception_handler(StarletteHTTPException)
async def spa_fallback(request: Request, exc: StarletteHTTPException):
    if (
        exc.status_code == 404
        and request.method == "GET"
        and not request.url.path.startswith(_API_PREFIXES)
    ):
        index = Path("static/index.html")
        if index.exists():
            return FileResponse(index)
    return JSONResponse(
        {"detail": exc.detail},
        status_code=exc.status_code,
        headers=getattr(exc, "headers", None),
    )


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    db_ok = False
    try:
        from sqlalchemy import text
        async for db in get_db():
            await db.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        model=settings.hf_model,
        hf_token_set=bool(settings.hf_token),
        db_connected=db_ok,
        odoo_url=settings.odoo_url or "(не задан)",
    )


@app.get("/roles", tags=["chat"])
async def get_roles():
    return {
        "roles": [
            {"id": "founder",   "name": "Помощник основателя",  "emoji": "🚀"},
            {"id": "investor",  "name": "Оценщик инвестора",    "emoji": "💼"},
            {"id": "mentor",    "name": "Ментор акселератора",  "emoji": "🎓"},
            {"id": "critic",    "name": "Жёсткий критик",       "emoji": "🔍"},
            {"id": "marketer",  "name": "Маркетолог (CMO)",     "emoji": "📊"},
            {"id": "financier", "name": "Финансист (CFO)",      "emoji": "💰"},
            {"id": "lawyer",    "name": "Юрист",                "emoji": "⚖️"},
        ]
    }


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat_stateless(request: ChatRequest):
    """Stateless чат — обратная совместимость."""
    if not settings.hf_token:
        raise HTTPException(status_code=500, detail="HF_TOKEN не задан")
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    try:
        reply, tokens, _ = await call_hf(role=request.role, messages=messages)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"HuggingFace ошибка: {e}")
    return ChatResponse(reply=reply, role=request.role, model=settings.hf_model, total_tokens=tokens)
