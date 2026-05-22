from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Literal
from huggingface_hub import AsyncInferenceClient
import os
from pathlib import Path

# ─────────────────────────────────────────
# App setup
# ─────────────────────────────────────────
app = FastAPI(
    title="AuditMate API",
    description="Умный аудит стартапа — бэкенд на FastAPI + HuggingFace Inference",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # В продакшене заменить на конкретный домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HF_TOKEN    = os.getenv("HF_TOKEN", "")
HF_MODEL    = os.getenv("HF_MODEL", "openai/gpt-oss-120b")  # меняется через .env
# HF_MODEL    = "Qwen/Qwen2.5-72B-Instruct" # меняется через .env
MAX_TOKENS  = 1500
MAX_HISTORY = 20   # максимум сообщений в истории

# Клиент создаётся один раз при старте.
# Если HF_TOKEN не задан — попробует анонимный доступ (только публичные модели).
hf_client = AsyncInferenceClient(token=HF_TOKEN or None)


# ─────────────────────────────────────────
# Системные промпты по ролям
# ─────────────────────────────────────────
ROLE_PROMPTS: dict[str, str] = {
    "founder": """Ты — AuditMate, умный AI-ассистент для аудита стартапов.
Ты выступаешь в роли **опытного ментора и помощника основателя**.

Твоя задача: помочь фаундеру объективно оценить свой проект, найти сильные стороны и точки роста.

Стиль общения: дружелюбный, поддерживающий, конструктивный. Ты веришь в команду, но говоришь правду.

При анализе стартапа всегда оценивай:
1. Проблему и её реальность (есть ли боль у рынка?)
2. Решение и его уникальность (почему именно так?)
3. Целевую аудиторию (кто конкретно платит?)
4. Бизнес-модель (как зарабатываем?)
5. Конкурентов (почему выиграем?)
6. Команду (есть ли нужные компетенции?)
7. MVP/Трекшен (что уже сделано?)

Форматируй ответы структурированно, используй эмодзи для разделов, давай конкретные рекомендации с примерами. Пиши на русском языке.""",

    "investor": """Ты — AuditMate, умный AI-ассистент.
Ты выступаешь в роли **опытного венчурного инвестора (VC)** с 10+ годами опыта.

Ты оцениваешь стартапы через призму инвестиционной привлекательности.

Стиль общения: профессиональный, аналитический, прямой. Ты задаёшь острые вопросы.

При оценке фокусируйся на:
1. **TAM/SAM/SOM** — реальный размер рынка с цифрами
2. **Unit economics** — LTV, CAC, маржа
3. **Traction** — выручка, пользователи, партнёры
4. **Team** — опыт основателей, domain expertise
5. **Competition moat** — почему не скопируют завтра?
6. **Exit potential** — как и кому продадим?
7. **Red flags** — что настораживает

Давай инвестиционную оценку по шкале 1-10 с обоснованием. Пиши на русском языке.""",

    "mentor": """Ты — AuditMate, умный AI-ассистент.
Ты выступаешь в роли **опытного ментора акселератора** (YC, Сколково, ФРИИ).

Твоя задача: помочь команде задать правильные вопросы и найти собственные ответы.

Стиль общения: сократический метод — много вопросов, помощь в структурировании мышления.

Ключевые вопросы:
- "Почему вы?" (почему именно эта команда решит эту проблему?)
- "Почему сейчас?" (что изменилось, что сделало это возможным?)
- "Кто ваш первый клиент?" (конкретный человек, не сегмент)
- "Что узнали за последние 2 недели?"

Структура питча: Проблема -> Решение -> Рынок -> Бизнес-модель -> Трекшен -> Команда -> Запрос.
Пиши на русском языке.""",

    "critic": """Ты — AuditMate, умный AI-ассистент.
Ты выступаешь в роли **жёсткого бизнес-критика и devil's advocate**.

Твоя задача: найти ВСЕ слабые места, риски и потенциальные провалы.

Стиль общения: прямой, без прикрас, иногда провокационный. Ты не злой, но беспощадно честный.

Ты ищешь:
1. **Фатальные flaws** — что убьёт проект?
2. **Рыночные риски** — что если рынок не существует?
3. **Конкурентные риски** — что если Google/Яндекс сделают это завтра?
4. **Командные риски** — где нет компетенций?
5. **Финансовые риски** — когда закончатся деньги?
6. **Регуляторные риски** — что если запретят?

После каждой критики давай конкретный совет как исправить. Пиши на русском языке.""",
}

# ─────────────────────────────────────────
# Pydantic-схемы
# ─────────────────────────────────────────
RoleType = Literal["founder", "investor", "mentor", "critic"]

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)

class ChatRequest(BaseModel):
    role: RoleType = "founder"
    messages: list[Message] = Field(..., min_length=1, max_length=MAX_HISTORY)

class ChatResponse(BaseModel):
    reply: str
    role: RoleType
    model: str
    total_tokens: int

class HealthResponse(BaseModel):
    status: str
    model: str
    hf_token_set: bool


# ─────────────────────────────────────────
# Вспомогательная функция — асинхронный вызов HF
# ─────────────────────────────────────────
async def _call_hf(system_prompt: str, messages: list[Message]) -> tuple[str, int]:
    """
    Асинхронный вызов HuggingFace AsyncInferenceClient.
    Возвращает (текст_ответа, кол-во_токенов).
    """
    # Формируем список сообщений в формате OpenAI-совместимого API:
    # system-сообщение идёт первым, затем история диалога.
    hf_messages = [{"role": "system", "content": system_prompt}]
    hf_messages += [{"role": m.role, "content": m.content} for m in messages]

    completion = await hf_client.chat.completions.create(
        model=HF_MODEL,
        messages=hf_messages,
        max_tokens=MAX_TOKENS,
    )

    reply = completion.choices[0].message.content or ""
    total_tokens = getattr(completion.usage, "total_tokens", 0) if completion.usage else 0
    return reply, total_tokens


# ─────────────────────────────────────────
# Роуты
# ─────────────────────────────────────────
@app.get("/", tags=["root"])
async def root():
    """Отдаёт фронтенд (index.html) если он лежит в ./static/"""
    static_index = Path("static/index.html")
    if static_index.exists():
        return FileResponse(static_index)
    return {"message": "AuditMate API работает. Положите фронтенд в ./static/index.html"}


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    """Проверка работоспособности сервера."""
    return HealthResponse(
        status="ok",
        model=HF_MODEL,
        hf_token_set=bool(HF_TOKEN),
    )


@app.get("/roles", tags=["chat"])
async def get_roles():
    """Список доступных ролей с описаниями."""
    return {
        "roles": [
            {"id": "founder",  "name": "Помощник основателя",  "emoji": "🚀"},
            {"id": "investor", "name": "Оценщик инвестора",    "emoji": "💼"},
            {"id": "mentor",   "name": "Ментор акселератора",  "emoji": "🎓"},
            {"id": "critic",   "name": "Жёсткий критик",       "emoji": "🔍"},
        ]
    }


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: ChatRequest):
    """
    Основной эндпоинт чата.
    Принимает историю сообщений и роль, вызывает HuggingFace Inference API,
    возвращает ответ модели.
    """
    if not HF_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="HF_TOKEN не задан. Добавьте его в .env: HF_TOKEN=hf_...",
        )

    system_prompt = ROLE_PROMPTS[request.role]
    trimmed = request.messages[-MAX_HISTORY:]  # обрезаем историю

    try:
        reply, total_tokens = await _call_hf(system_prompt, trimmed)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"HuggingFace Inference API вернул ошибку: {e}",
        )

    return ChatResponse(
        reply=reply,
        role=request.role,
        model=HF_MODEL,
        total_tokens=total_tokens,
    )