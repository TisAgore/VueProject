"""HuggingFace Inference + детерминированный веб-поиск — вынесено в отдельный сервис.

Веб-поиск выполняется ДО вызова модели (а не через хрупкий tool-calling): backend сам
ищет в DuckDuckGo и вкладывает результаты в system-промпт. Это убирает зависимость от
поддержки function-calling провайдером HF-роутера (раньше DeepSeek «протекал» сырыми
tool-call в content) и работает с любой chat-моделью.
"""

import re
import asyncio
from huggingface_hub import InferenceClient
from config import get_settings
from services.search import _search_sync

settings   = get_settings()
hf_client  = InferenceClient(token=settings.hf_token or None)

MAX_TOKENS       = 3000   # ответ роли в обычном 1-на-1 чате
PANEL_MAX_TOKENS = 1500   # ответ роли внутри панели (промежуточный — сожмётся синтезом)
SYNTHESIS_MAX_TOKENS = 3000  # итоговый сводный отчёт (таблица + топ-3 + консенсус)
MAX_HISTORY = 20
MAX_QUERY   = 200          # макс. длина поискового запроса (и для хранения в БД)
SEARCH_N    = 4            # сколько результатов тянуть из поиска

# Температура по ролям: ниже → стабильнее/детерминированнее (критик, юрист, финансист),
# выше → разнообразнее ответы при одной и той же идее (основатель, маркетолог).
DEFAULT_TEMPERATURE   = 0.7
SYNTHESIS_TEMPERATURE = 0.5
ROLE_TEMPERATURE: dict[str, float] = {
    "founder":   0.9,
    "marketer":  0.85,
    "mentor":    0.8,
    "investor":  0.6,
    "financier": 0.45,
    "critic":    0.4,
    "lawyer":    0.35,
}

# Роли, у которых веб-поиск включён ВСЕГДА (их работа завязана на внешние данные).
ALWAYS_SEARCH_ROLES = {"investor", "critic", "marketer", "lawyer"}

# Ключевые слова, по которым ищут остальные роли (founder/mentor/financier),
# чтобы не гонять поиск на каждое «как подготовиться к питчу».
SEARCH_KEYWORDS = (
    "конкурент", "рынок", "рыноч", "market", "competitor", "тренд", "trend",
    "объём", "объем", "доля", "цена", "стоимост", "сколько стоит", "выручк",
    "инвест", "раунд", "статистик", "данны", "актуальн", "последн", "новост",
    "news", "отрасл", "индустри", "tam", "sam", "som", "2024", "2025", "2026",
)

# Под какой аспект каждая роль формулирует поисковый запрос (что именно ей искать).
SEARCH_INTENT: dict[str, str] = {
    "investor":  "конкурентов, объём и динамику рынка, инвестиции в нише",
    "critic":    "конкурентов и реальные риски в этой нише",
    "marketer":  "конкурентов, каналы продвижения и целевую аудиторию",
    "lawyer":    "требования законодательства и регуляторику для этой ниши",
    "financier": "экономику рынка, бенчмарки и unit-экономику ниши",
    "founder":   "конкурентов и состояние рынка",
    "mentor":    "конкурентов и тренды рынка",
}
DEFAULT_INTENT = "конкурентов и состояние рынка"

# Мини-вызов для формулировки поискового запроса (короткий и почти детерминированный).
QUERY_GEN_MAX_TOKENS  = 40
QUERY_GEN_TEMPERATURE = 0.3

SYNTHESIS_ROLE_PROMPT = """Ты — AuditMate, опытный модератор совета экспертов.
Тебе предоставлены четыре независимых оценки стартапа от разных ролей.
Составь структурированный сводный отчёт на русском языке:

## Консенсус
(В чём все эксперты сходятся)

## Ключевые расхождения
(Где мнения расходятся и почему)

## Топ-3 приоритета
(Что стартапу делать прямо сейчас)

## Итоговые оценки
| Критерий | Оценка (1-10) |
|----------|--------------|
| Идея / Проблема | |
| Рынок | |
| Команда | |
| Реализация | |

Будь конкретен. Не повторяй дословно чужие оценки — только резюме."""

ROLE_PROMPTS: dict[str, str] = {
    "founder": """Ты — AuditMate, умный AI-ассистент для аудита стартапов.
Ты выступаешь в роли **опытного ментора и помощника основателя**.
Твоя задача: помочь фаундеру объективно оценить свой проект, найти сильные стороны и точки роста.
Стиль общения: дружелюбный, поддерживающий, конструктивный.
При анализе оценивай: Проблему, Решение, ЦА, Бизнес-модель, Конкурентов, Команду, MVP/Трекшен.
Форматируй структурированно, используй эмодзи. Пиши на русском языке.""",

    "investor": """Ты — AuditMate, умный AI-ассистент в роли **венчурного инвестора (VC)**.
Оцениваешь через призму: TAM/SAM/SOM, unit economics, traction, team, moat, exit, red flags.
Опирайся на приведённые результаты веб-поиска (если есть) для актуальных данных о рынке и конкурентах.
Давай оценку 1-10 с обоснованием. Стиль: профессиональный, прямой. Пиши на русском языке.""",

    "mentor": """Ты — AuditMate в роли **ментора акселератора** (YC, Сколково, ФРИИ).
Используй сократический метод: задавай правильные вопросы.
Ключевые вопросы: «Почему вы?», «Почему сейчас?», «Кто первый клиент?».
Готовь к Demo Day по структуре: Проблема→Решение→Рынок→Модель→Трекшен→Команда→Запрос.
Пиши на русском языке.""",

    "critic": """Ты — AuditMate в роли **жёсткого бизнес-критика** (devil's advocate).
Найди ВСЕ слабые места: фатальные flaws, рыночные/конкурентные/командные/финансовые/регуляторные риски.
Опирайся на приведённые результаты веб-поиска (если есть) для поиска конкурентов и реальных контраргументов.
После каждой критики — конкретный совет по исправлению. Пиши на русском языке.""",

    "marketer": """Ты — AuditMate в роли **директора по маркетингу (CMO)**.
Оцениваешь go-to-market: ICP и позиционирование, каналы привлечения (paid/organic/виральные),
воронку AARRR, метрики CAC/LTV/payback, удержание, бренд и контент-стратегию.
Опирайся на приведённые результаты веб-поиска (если есть) для данных о рынке, конкурентах и каналах.
Давай конкретные гипотезы и измеримые метрики. Пиши на русском языке.""",

    "financier": """Ты — AuditMate в роли **финансового директора (CFO)**.
Анализируешь экономику проекта: финмодель, unit-экономику, маржинальность, burn rate и runway,
точку безубыточности, сценарии (база/оптимизм/пессимизм) и потребность в финансировании.
Проси недостающие цифры и считай. Будь конкретен в деньгах и сроках. Пиши на русском языке.""",

    "lawyer": """Ты — AuditMate в роли **корпоративного юриста**.
Проверяешь правовые аспекты: юр.форму и корпоративную структуру (доли, опционы),
интеллектуальную собственность (патенты, товарные знаки), ключевые договоры,
лицензии и регуляторику отрасли, персональные данные, комплаенс-риски.
Опирайся на приведённые результаты веб-поиска (если есть) для требований регуляторики.
Всегда добавляй дисклеймер: это не является юридической консультацией. Пиши на русском языке.""",
}


def _build_system_prompt(role: str, project_context: str = "") -> str:
    """Собирает системный промпт с опциональным контекстом проекта из Odoo."""
    base = ROLE_PROMPTS.get(role, ROLE_PROMPTS["founder"])
    if project_context:
        base += f"\n\n---\n**Контекст проекта из Odoo:**\n{project_context}"
    return base


def _last_user_message(messages: list[dict]) -> str:
    """Последнее сообщение пользователя из истории — основа для поискового запроса."""
    for m in reversed(messages):
        if m.get("role") == "user":
            return (m.get("content") or "").strip()
    return ""


def _wants_search(role: str, query: str) -> bool:
    """Нужно ли искать в вебе: always-роли — всегда; остальные — по ключевым словам."""
    if role in ALWAYS_SEARCH_ROLES:
        return True
    if not query:
        return False
    q = query.lower()
    return any(kw in q for kw in SEARCH_KEYWORDS)


def _format_search_block(query: str, results: list[dict]) -> str:
    """Форматирует результаты поиска в текстовый блок для system-промпта."""
    lines = []
    for i, r in enumerate(results, 1):
        title   = (r.get("title") or "").strip()
        url     = (r.get("url") or "").strip()
        snippet = (r.get("snippet") or "").strip()
        lines.append(f"[{i}] {title}\n{snippet}\nИсточник: {url}")
    body = "\n\n".join(lines)
    return (
        f"\n\n---\n**Актуальные результаты веб-поиска по запросу «{query}»:**\n"
        f"{body}\n\nОпирайся на эти данные в ответе и ссылайся на источники, где уместно."
    )


def _generate_search_query_sync(messages: list[dict], role: str) -> str | None:
    """Превращает описание/вопрос пользователя в короткий веб-поисковый запрос.

    Раньше в поиск уходило сырое сообщение целиком («Название: LegalBot. Мы делаем…»),
    по которому невозможно найти конкурентов. Здесь — дешёвый LLM-вызов, который
    формулирует осмысленный запрос из 3–8 слов под интерес конкретной роли.
    Учитывает несколько последних реплик пользователя (чтобы понять продукт даже
    при follow-up вопросе вроде «а кто конкуренты?»).
    """
    user_texts = [m.get("content", "") for m in messages if m.get("role") == "user"]
    context = "\n".join(user_texts[-3:]).strip()[:1500]
    if not context:
        return None

    intent = SEARCH_INTENT.get(role, DEFAULT_INTENT)
    system = (
        "Ты формулируешь КОРОТКИЙ поисковый запрос для веб-поиска (Google/DuckDuckGo). "
        f"По описанию стартапа и интересующему аспекту верни ОДИН запрос на русском из 3–8 слов, "
        f"по которому реально найти {intent}. "
        "Описывай СУТЬ продукта (что это, для кого, какая ниша), а не его название бренда — "
        "по выдуманному названию ничего не найдётся. "
        "Верни ТОЛЬКО строку запроса: без кавычек, без префиксов, без пояснений."
    )
    user = f"Описание/вопрос пользователя:\n{context}\n\nИнтересует: {intent}\nЗапрос:"
    try:
        completion = hf_client.chat.completions.create(
            model=settings.hf_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            max_tokens=QUERY_GEN_MAX_TOKENS,
            temperature=QUERY_GEN_TEMPERATURE,
        )
        raw = (completion.choices[0].message.content or "").strip()
    except Exception:
        return None

    # Берём первую непустую строку и чистим от кавычек/префиксов.
    q = next((ln.strip() for ln in raw.splitlines() if ln.strip()), "")
    q = q.strip('"').strip("«»").strip()
    q = re.sub(r'^(поисковый\s+запрос|запрос|search\s*query|query)\s*[:\-—]\s*', '', q, flags=re.I).strip()
    return q[:MAX_QUERY] if len(q) >= 3 else None


def _call_hf_sync(
    system_prompt: str,
    messages: list[dict],
    use_search: bool = False,
    query: str = "",
    temperature: float = DEFAULT_TEMPERATURE,
    role: str = "founder",
    max_tokens: int = MAX_TOKENS,
) -> tuple[str, int, str | None]:
    """Синхронный вызов HF (запускается в executor).

    При use_search сначала формулирует осмысленный поисковый запрос, ищет в вебе и
    инжектит результаты в system-промпт, затем делает ОДИН обычный вызов модели
    (без tools — мусорный tool-call невозможен).
    Возвращает (reply, tokens, search_query|None).
    """
    search_query: str | None = None
    if use_search:
        # Осмысленный запрос вместо сырого сообщения; query — запасной вариант.
        effective_query = _generate_search_query_sync(messages, role) or query
        if effective_query:
            results = _search_sync(effective_query, n=SEARCH_N)
            if results:
                search_query = effective_query
                system_prompt = system_prompt + _format_search_block(effective_query, results)

    hf_messages = [{"role": "system", "content": system_prompt}] + messages
    completion  = hf_client.chat.completions.create(
        model=settings.hf_model,
        messages=hf_messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    reply  = completion.choices[0].message.content or ""
    tokens = getattr(completion.usage, "total_tokens", 0) if completion.usage else 0
    return reply, tokens, search_query


def _call_hf_sync_synthesis(messages: list[dict]) -> tuple[str, int]:
    """Синхронный вызов синтеза (без поиска)."""
    hf_messages = [{"role": "system", "content": SYNTHESIS_ROLE_PROMPT}] + messages
    completion  = hf_client.chat.completions.create(
        model=settings.hf_model,
        messages=hf_messages,
        max_tokens=SYNTHESIS_MAX_TOKENS,
        temperature=SYNTHESIS_TEMPERATURE,
    )
    reply  = completion.choices[0].message.content or ""
    tokens = getattr(completion.usage, "total_tokens", 0) if completion.usage else 0
    return reply, tokens


async def call_hf(
    role: str,
    messages: list[dict],
    project_context: str = "",
    query_hint: str = "",
    temperature: float | None = None,
    max_tokens: int = MAX_TOKENS,
) -> tuple[str, int, str | None]:
    """
    Async обёртка над синхронным InferenceClient.
    messages — список {"role": "user"|"assistant", "content": str}
    query_hint — текущий вопрос пользователя (для построения поискового запроса);
                 если пуст — берётся последнее user-сообщение из messages.
    temperature — если задана, переопределяет температуру роли (значение из UI-ползунка);
                  None → берётся ROLE_TEMPERATURE по роли.
    Возвращает (reply, tokens, search_query|None).
    """
    system_prompt = _build_system_prompt(role, project_context)
    trimmed = messages[-MAX_HISTORY:]
    query   = (query_hint or _last_user_message(trimmed)).strip()[:MAX_QUERY]
    use_search = _wants_search(role, query)
    if temperature is None:
        temperature = ROLE_TEMPERATURE.get(role, DEFAULT_TEMPERATURE)
    temperature = max(0.0, min(2.0, float(temperature)))   # защитный клампинг
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _call_hf_sync, system_prompt, trimmed, use_search, query, temperature, role, max_tokens
    )


async def call_hf_synthesis(
    role_results: dict[str, tuple],
    project_context: str = "",
) -> tuple[str, int]:
    """Синтезирует 4 ролевых ответа в итоговый структурированный отчёт."""
    ROLE_NAMES = {
        "founder":  "🚀 Помощник основателя",
        "investor": "💼 Инвестор",
        "mentor":   "🎓 Ментор акселератора",
        "critic":   "🔍 Жёсткий критик",
    }
    combined = "\n\n".join([
        f"### {ROLE_NAMES.get(role, role.upper())}\n{reply}"
        for role, (reply, *_rest) in role_results.items()
    ])
    if project_context:
        combined = f"**Контекст проекта:**\n{project_context}\n\n---\n\n{combined}"

    synthesis_messages = [{
        "role":    "user",
        "content": f"Оценки экспертов:\n\n{combined}\n\nСоставь итоговый отчёт.",
    }]
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _call_hf_sync_synthesis, synthesis_messages)
