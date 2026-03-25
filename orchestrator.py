import json
import time
import os
from dotenv import load_dotenv
import argparse

from dataclasses import dataclass, asdict
from typing import Optional
import concurrent.futures

from openai import OpenAI
from openai import RateLimitError
import random

# region Выбор модели
CLOUD_MODELS: dict[str, dict] = {
    # не работает
    "gptoss20b": {
        "id": "openai/gpt-oss-20b:free",
        "label": "GPT-OSS 20B",
        "provider": "Openrouter",
    },
    # не работает
    "gptoss120b": {
        "id": "openai/gpt-oss-120b:free",
        "label": "GPT-OSS 120B",
        "provider": "Openrouter",
    },
    # не работает
    "qwen3": {
        "id": "qwen/qwen3-4b:free",
        "label": "Qwen3 4B",
        "provider": "Openrouter",
    },
    # не работает
    "llama3.3": {
        "id": "meta-llama/llama-3.3-70b-instruct:free",
        "label": "Llama 3.3 70B",
        "provider": "Openrouter",
    },
    # не работает
    "llama3.2.3": {
        "id": "meta-llama/llama-3.2-3b-instruct:free",
        "label": "Llama 3.2.3 3B",
        "provider": "Openrouter",
    },
    # не работает
    "gemma3": {
        "id": "google/gemma-3-12b-it:free",
        "label": "Gemma3 12b",
        "provider": "Openrouter",
    },
    # ✅ РАБОТАЕТ
    "trinity": {
        "id": "arcee-ai/trinity-mini:free",
        "label": "Trinity mini",
        "provider": "Openrouter",
    },
    # Работает через раз
    "nemotron30b": {
        "id": "nvidia/nemotron-3-nano-30b-a3b:free",
        "label": "Nemotron Nano 30B",
        "provider": "Openrouter",
    },
    # Работает через раз
    "nemotron9b": {
        "id": "nvidia/nemotron-3-nano-30b-a3b:free",
        "label": "Nemotron Nano 9B",
        "provider": "Openrouter",
    },
}

LOCAL_MODELS: dict[str, dict] = {
    "local": {
        "id": "auto",
        "label": "LM Studio (активная модель)",
        "provider": "lmstudio",
    },
    "qwen2.5-3b": {
        "id": "qwen2.5-3b-instruct",
        "label": "Qwen2.5 3B Instruct",
        "provider": "lmstudio",
        "note": "~2 GB VRAM",
    },
    "qwen2.5-7b": {
        "id": "qwen2.5-7b-instruct",
        "label": "Qwen2.5 7B Instruct",
        "provider": "lmstudio",
        "note": "~5 GB VRAM",
    },
    "llama3.2-3b": {
        "id": "llama-3.2-3b-instruct",
        "label": "Llama 3.2 3B Instruct",
        "provider": "lmstudio",
        "note": "~2.5 GB VRAM",
    },
    "phi3.5-mini": {
        "id": "phi-3.5-mini-instruct",
        "label": "Phi-3.5 Mini Instruct",
        "provider": "lmstudio",
        "note": "~2.5 GB VRAM",
    },
    "gemma3-4b": {
        "id": "gemma-3-4b-it",
        "label": "Gemma 3 4B Instruct",
        "provider": "lmstudio",
        "note": "~3 GB VRAM",
    },
}

ALL_MODELS = {**CLOUD_MODELS, **LOCAL_MODELS}

DEFAULT_MODEL_KEY = "gptoss20b"
LMSTUDIO_BASE_URL = "http://localhost:1234/v1"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_openrouter_client() -> OpenAI:
    """Создаёт OpenAI-совместимый клиент для OpenRouter."""

    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise EnvironmentError(
            "Переменная окружения OPENROUTER_API_KEY не задана."
        )

    return OpenAI(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
    )


def get_lmstudio_client(base_url: str = LMSTUDIO_BASE_URL) -> OpenAI:
    """
    LM Studio поднимает OpenAI-совместимый сервер на localhost:1234.
    API-ключ не нужен.
    """

    return OpenAI(api_key="lm-studio", base_url=base_url)


def get_client_for_model(model_key: str, lmstudio_url: str = LMSTUDIO_BASE_URL) -> OpenAI:
    """Возвращает нужный клиент в зависимости от провайдера модели."""

    info = ALL_MODELS.get(model_key)

    if info and info["provider"] == "lmstudio":
        return get_lmstudio_client(lmstudio_url)

    return get_openrouter_client()


def resolve_model_id(model_key: str) -> str:
    """
    Принимает ключ ('gptoss20b', 'qwen3', 'llama3.3') или полный model id.
    Возвращает строку model id для API.
    """

    if model_key in ALL_MODELS:
        mid = ALL_MODELS[model_key]["id"]

        return "" if mid == "auto" else mid

    return model_key


def is_local(model_key: str) -> bool:
    return ALL_MODELS.get(model_key, {}).get("provider") == "lmstudio"


def print_available_models():
    print("\n☁️  Облачные модели (OpenRouter):")

    for key, info in CLOUD_MODELS.items():
        print(f"  {key:<14} — {info['label']}")

    print("\n💻 Локальные модели (LM Studio):")

    for key, info in LOCAL_MODELS.items():
        note = info.get("note", "")
        print(f"  {key:<14} — {info['label']}")

        if note:
            print(f"  {'':14}   ↳ {note}")

    print()


# endregion


# region Конфигурация агентов
AGENT_DEFINITIONS: dict[str, dict] = {
    "optimist": {
        "name": "Венчурный Оптимист",
        "emoji": "🚀",
        "temperature": 0.75,
        "system": """Ты — старший партнёр топового венчурного фонда с 20-летним опытом.
    Ты специализируешься на поиске скрытых «бриллиантов» — стартапов с потенциалом 100x,
    которые другие аналитики недооценивают.

    Твоя задача: найти ВСЕ сильные стороны стартапа. Смотри на:
    - Уникальность ценностного предложения и инсайт фаундеров
    - Защищаемые конкурентные преимущества (network effects, IP, data moat)
    - Качество и релевантность команды
    - Тайминг — почему именно сейчас этот рынок созрел
    - Признаки product-market fit или сильные гипотезы
    - Скрытый потенциал, который не очевиден с первого взгляда

    Будь конкретен. Ссылайся на реальные данные из питча. Избегай пустых комплиментов.
    Всегда отвечай на русском языке.

    ВАЖНО: Верни ответ СТРОГО в формате JSON (без markdown, без пояснений до/после):
    {
      "strengths": [
        {"point": "название", "detail": "подробное объяснение с данными из питча", "impact": "high|medium|low"}
      ],
      "hidden_gems": ["неочевидное преимущество 1", "неочевидное преимущество 2"],
      "best_case_scenario": "описание лучшего сценария развития (2-3 предложения)",
      "score": 7,
      "score_rationale": "почему именно такой балл"
    }""",
    },

    "critic": {
        "name": "Скептичный Аналитик",
        "emoji": "🔍",
        "temperature": 0.4,
        "system": """Ты — партнёр по due diligence в крупном PE-фонде.
    Твоя работа — предотвращать плохие инвестиции. Ты видел сотни питчей и знаешь,
    как фаундеры украшают реальность. Твой профессиональный скептицизм спас фонд
    от множества катастроф.

    Твоя задача: найти ВСЕ слабые стороны и риски. Анализируй:
    - Дыры в бизнес-модели и нереалистичные юнит-экономические предположения
    - Завышенные оценки TAM или ошибочные расчёты
    - Конкурентные угрозы, которые фаундеры игнорируют или недооценивают
    - Риски команды: пробелы в экспертизе, красные флаги, зависимость от ключевых людей
    - Регуляторные, технологические и рыночные риски
    - Что фаундеры НЕ сказали (умолчания часто важнее слов)
    - Execution risks — почему именно эта команда может не справиться

    Не смягчай. Инвестор должен знать худшее до того, как подпишет чек.
    Всегда отвечай на русском языке.

    ВАЖНО: Верни ответ СТРОГО в формате JSON (без markdown, без пояснений до/после):
    {
      "weaknesses": [
        {"point": "название", "detail": "подробное объяснение", "severity": "critical|high|medium|low"}
      ],
      "risks": [
        {"risk": "название риска", "probability": "high|medium|low", "impact": "high|medium|low", "mitigation_possible": true}
      ],
      "red_flags": ["тревожный сигнал 1", "тревожный сигнал 2"],
      "worst_case_scenario": "описание худшего сценария (2-3 предложения)",
      "score": 4,
      "score_rationale": "почему именно такой балл"
    }""",
    },

    "market_analyst": {
        "name": "Рыночный Аналитик",
        "emoji": "📊",
        "temperature": 0.3,
        "system": """Ты — независимый рыночный аналитик с глубокой экспертизой в оценке
    размеров рынков, конкурентных ландшафтов и рыночного тайминга.

    Твоя задача: дать объективную оценку рыночной позиции стартапа:
    - Реалистичность заявленного TAM/SAM/SOM (часто завышены в 10-100x)
    - Текущий конкурентный ландшафт: прямые и косвенные конкуренты
    - Барьеры входа и сложность для новых игроков
    - Тайминг: рынок перегрет, недозрел или в точке inflection?
    - Тренды, которые помогают или угрожают этой нише
    - Как стартап позиционируется относительно конкурентов

    Будь точен в цифрах. Если данные в питче сомнительны — укажи это явно.
    Всегда отвечай на русском языке.

    ВАЖНО: Верни ответ СТРОГО в формате JSON (без markdown, без пояснений до/после):
    {
      "market_size": {
        "tam_assessment": "реалистичная оценка TAM с пояснением",
        "tam_realistic": "X млрд $",
        "credibility": "credible|overstated|understated"
      },
      "competitive_landscape": {
        "direct_competitors": ["конкурент 1", "конкурент 2"],
        "indirect_competitors": ["косвенный 1"],
        "differentiation_clarity": "clear|unclear|weak"
      },
      "timing_verdict": "too_early|perfect|too_late|unclear",
      "timing_rationale": "почему именно такой вердикт по таймингу",
      "market_tailwinds": ["тренд в пользу 1", "тренд в пользу 2"],
      "market_headwinds": ["тренд против 1"],
      "score": 6,
      "score_rationale": "почему именно такой балл"
    }""",
    },

    "team_evaluator": {
        "name": "Эксперт по Командам",
        "emoji": "👥",
        "temperature": 0.5,
        "system": """Ты — эксперт по оценке команд стартапов. За твоими плечами —
    оценка сотен фаундерских команд, ты понимаешь разницу между теми,
    кто строит и теми, кто только презентует.

    Твоя задача: глубокая оценка команды:
    - Релевантность опыта фаундеров именно для этой проблемы
    - «Unfair advantage» — есть ли у команды уникальный доступ к рынку, технологии или клиентам
    - Комплементарность навыков: закрыты ли ключевые роли (tech, biz, domain)
    - Признаки coachability и адаптивности
    - История: что уже построили, что доказали
    - Execution signals: метрики, traction, скорость прогресса
    - Potential gaps: кого не хватает в команде

    Инвесторы вкладывают в людей, а не в идеи.
    Всегда отвечай на русском языке.

    ВАЖНО: Верни ответ СТРОГО в формате JSON (без markdown, без пояснений до/после):
    {
      "team_strengths": ["сила 1", "сила 2"],
      "team_gaps": [
        {"gap": "что отсутствует", "criticality": "critical|high|medium|low", "fixable": true}
      ],
      "unfair_advantage": "описание уникального преимущества команды или 'не выявлено'",
      "execution_signals": ["сигнал 1", "сигнал 2"],
      "founder_market_fit": "strong|medium|weak",
      "founder_market_fit_rationale": "почему",
      "score": 7,
      "score_rationale": "почему именно такой балл"
    }""",
    },
}

SYNTHESIZER_SYSTEM = """Ты — председатель инвестиционного комитета.
Ты получил независимые отчёты от четырёх специализированных аналитиков.
Твоя задача — синтезировать их в итоговое инвестиционное заключение.

Правила синтеза:
1. Не просто усредняй баллы — объясни природу разногласий между аналитиками
2. Взвешивай баллы: рынок×0.25, команда×0.30, сильные стороны×0.25, риски×0.20
3. Если есть CRITICAL риски — это может быть блокером независимо от остальных оценок
4. Инвестиционная рекомендация должна быть однозначной: одно из трёх значений
5. Всегда отвечай на русском языке.

ВАЖНО: Верни ответ СТРОГО в формате JSON (без markdown, без пояснений до/после):
{
  "executive_summary": "2-3 предложения о стартапе в целом",
  "weighted_score": 6.5,
  "score_breakdown": {
    "strengths": 7,
    "weaknesses_and_risks": 4,
    "market": 6,
    "team": 7
  },
  "key_conflicts": [
    {"conflict": "в чём разошлись аналитики", "resolution": "как комитет это разрешает"}
  ],
  "investment_recommendation": "invest|pass|more_diligence",
  "recommendation_rationale": "почему именно эта рекомендация (3-5 предложений)",
  "critical_blockers": ["блокер если есть"],
  "conditions_to_invest": ["условие 1 если рекомендация more_diligence"],
  "next_steps": ["конкретный следующий шаг 1", "конкретный следующий шаг 2"]
}"""
# endregion


# region Dataclasses
@dataclass
class AgentResult:
    agent_key: str
    agent_name: str
    emoji: str
    model_used: str
    provider: str
    raw_response: str
    parsed: Optional[dict]
    duration_ms: int
    error: Optional[str] = None


@dataclass
class CommitteeReport:
    pitch_excerpt: str
    model_key: str
    sequential: bool
    agent_results: list[AgentResult]
    synthesis: Optional[dict]
    total_duration_ms: int
    timestamp: str


# endregion


# region Вспомогательные функции
def _strip_json(text: str) -> str:
    """Убирает markdown-обёртки ```json ... ``` если модель их добавила."""

    t = text.strip()

    if t.startswith("```"):
        lines = t.splitlines()
        end = next(
            (i for i in range(len(lines) - 1, 0, -1) if lines[i].strip() == "```"),
            None,
        )
        inner = lines[1:end] if end else lines[1:]
        t = "\n".join(inner).strip()

    return t


def _build_request_kwargs(model_id: str, system: str, user: str, temperature: float, provider: str) -> dict:
    """
    Собирает kwargs для client.chat.completions.create().
    Для LM Studio: reasoning отключён (не поддерживается локально).
    Для OpenRouter: reasoning включён.
    """

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    kwargs: dict = {
        "max_tokens": 2000,
        "temperature": temperature,
        "messages": messages,
    }

    if model_id:
        kwargs["model"] = model_id

    if provider == "openrouter":
        kwargs["extra_body"] = {"reasoning": {"enabled": True}}

    return kwargs


def _call_with_retry(
        client: OpenAI,
        kwargs: dict,
        max_retries: int = 3,
        base_delay: float = 2.0,
):
    """
    Выполняет запрос к API с автоматическим повтором при rate-limit (429).

    Стратегия: exponential backoff с jitter.
      Попытка 1 → ждём base_delay  ± jitter
      Попытка 2 → ждём base_delay*2 ± jitter
      Попытка 3 → ждём base_delay*4 ± jitter
      ...

    Если в заголовке ответа есть Retry-After — используем его вместо backoff.
    Все остальные исключения (4xx кроме 429, сетевые ошибки) пробрасываются сразу.
    """

    attempt = 0

    while True:
        try:
            return client.chat.completions.create(**kwargs)

        except RateLimitError as e:
            attempt += 1
            if attempt > max_retries:
                raise

            retry_after = None
            if hasattr(e, "response") and e.response is not None:
                retry_after_raw = e.response.headers.get("Retry-After")
                if retry_after_raw:
                    try:
                        retry_after = float(retry_after_raw)
                    except ValueError:
                        pass

            if retry_after:
                wait = retry_after + random.uniform(0.5, 1.5)
            else:
                # exponential backoff: 2, 4, 8, 16 … сек + jitter
                wait = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)

            print(
                f"   429 Rate limit — попытка {attempt}/{max_retries}, "
                f"жду {wait:.1f}s..."
            )
            time.sleep(wait)


# endregion


# region Запуск одного агента
def run_agent_sync(
        agent_key: str,
        definition: dict,
        model_key: str,
        pitch_text: str,
        lmstudio_url: str,
        max_retries: int = 3,
) -> AgentResult:
    model_id = resolve_model_id(model_key)
    provider = ALL_MODELS.get(model_key, {}).get("provider", "openrouter")
    client = get_lmstudio_client(lmstudio_url) if provider == "lmstudio" else get_openrouter_client()

    start = time.time()

    try:
        kwargs = _build_request_kwargs(
            model_id=model_id,
            system=definition["system"],
            user=f"Проанализируй питч-дек стартапа:\n\n---\n{pitch_text}\n---",
            temperature=definition["temperature"],
            provider=provider,
        )
        response = _call_with_retry(client, kwargs, max_retries=max_retries)
        raw = response.choices[0].message.content.strip()

        try:
            parsed = json.loads(_strip_json(raw))
        except json.JSONDecodeError as e:
            return AgentResult(
                agent_key=agent_key, agent_name=definition["name"],
                emoji=definition["emoji"], model_used=model_id or "auto",
                provider=provider, raw_response=raw, parsed=None,
                duration_ms=int((time.time() - start) * 1000),
                error=f"JSON parse error: {e}",
            )

        return AgentResult(
            agent_key=agent_key, agent_name=definition["name"],
            emoji=definition["emoji"], model_used=model_id or "auto",
            provider=provider, raw_response=raw, parsed=parsed,
            duration_ms=int((time.time() - start) * 1000),
        )

    except Exception as e:
        err = str(e)

        if provider == "lmstudio" and ("Connection refused" in err or "connect" in err.lower()):
            err = (
                "Не удалось подключиться к LM Studio.\n"
                "  1. Открой LM Studio → вкладка 'Local Server'\n"
                "  2. Загрузи модель (например Qwen2.5 3B Instruct Q4_K_M)\n"
                "  3. Нажми 'Start Server' (порт 1234)\n"
                f"  URL: {lmstudio_url}"
            )

        return AgentResult(
            agent_key=agent_key, agent_name=definition["name"],
            emoji=definition["emoji"], model_used=model_id or "auto",
            provider=provider, raw_response="", parsed=None,
            duration_ms=int((time.time() - start) * 1000),
            error=err,
        )


# endregion


# region Синтезатор
def run_synthesizer(
        agent_results: list[AgentResult],
        synthesizer_model: str,
        lmstudio_url: str,
        max_retries: int = 3,
) -> Optional[dict]:
    reports = {
        ar.agent_key: {"name": ar.agent_name, "report": ar.parsed}
        for ar in agent_results if ar.parsed
    }

    if not reports:
        print("  ⚠️  Нет успешных отчётов агентов — синтез невозможен.")

        return None

    provider = ALL_MODELS.get(synthesizer_model, {}).get("provider", "openrouter")
    model_id = resolve_model_id(synthesizer_model)
    client = get_lmstudio_client(lmstudio_url) if provider == "lmstudio" else get_openrouter_client()

    user_msg = (
        f"Отчёты аналитиков:\n"
        f"{json.dumps(reports, ensure_ascii=False, indent=2)}\n\n"
        f"Создай итоговое инвестиционное заключение комитета."
    )

    try:
        kwargs = _build_request_kwargs(
            model_id=model_id,
            system=SYNTHESIZER_SYSTEM,
            user=user_msg,
            temperature=0.3,
            provider=provider,
        )

        response = _call_with_retry(client, kwargs, max_retries=max_retries)
        raw = response.choices[0].message.content.strip()
        return json.loads(_strip_json(raw))

    except Exception as e:
        print(f"  ❌ Synthesizer error: {e}")

        return None


# endregion


# region Запуск агентов
def evaluate_pitch(
        pitch_text: str,
        model_key: str = DEFAULT_MODEL_KEY,
        synthesizer_model: Optional[str] = None,
        per_agent_models: Optional[dict[str, str]] = None,
        lmstudio_url: str = LMSTUDIO_BASE_URL,
        sequential: Optional[bool] = None,
        delay: float = 0.0,
        max_retries: int = 3,
) -> CommitteeReport:
    """
    Запускает комитет агентов, затем синтезирует результаты.

    Args:
        pitch_text:         текст питч-дека
        model_key:          модель для всех агентов.
                            Ключи: gptoss20b, gptoss120b, qwen3, llama3.2.3, llama3.3, gemma3,
                                   local, qwen2.5-3b, qwen2.5-7b, llama3.2-3b, phi3.5-mini, gemma3-4b
        synthesizer_model:  модель для синтезатора (по умолчанию = model_key).
        per_agent_models:   точечные переопределения: {"critic": "llama"}
        lmstudio_url:       URL сервера LM Studio (по умолчанию localhost:1234)
        sequential:         True  — агенты строго по одному.
                            False — параллельно.
                            None  — авто: локальная → sequential, облако → parallel.
        delay:              Пауза в секундах между агентами в sequential-режиме.
                            Полезно при жёстких rate-limit окнах (RPM).
                            Игнорируется в параллельном режиме.
        max_retries:        Максимум повторов при 429 Rate Limit (для каждого агента
                            и синтезатора независимо). По умолчанию 3.

    Примеры:
        # Облачная модель, параллельно — retry при 429 включён автоматически
        report = evaluate_pitch(pitch, model_key="qwen")

        # Последовательно с паузой 5с между агентами (мягкий rate-limit)
        report = evaluate_pitch(pitch, model_key="gptoss", sequential=True, delay=5)

        # Агрессивный retry — до 6 попыток на каждый запрос
        report = evaluate_pitch(pitch, model_key="llama", max_retries=6)

        # Агенты локально, синтезатор в облаке
        report = evaluate_pitch(pitch, model_key="qwen2.5-7b", synthesizer_model="gptoss")
    """
    per_agent_models = per_agent_models or {}
    synthesizer_model = synthesizer_model or model_key

    # Автовыбор режима: локальная модель → sequential по умолчанию
    if sequential is None:
        sequential = is_local(model_key)

    total_start = time.time()

    model_info = ALL_MODELS.get(model_key, {})
    label = model_info.get("label", model_key)
    provider = model_info.get("provider", "openrouter")
    synth_info = ALL_MODELS.get(synthesizer_model, {})
    mode_label = "последовательная" if sequential else "параллельная"

    print(f"\nЗапущена [{mode_label}] обработка")
    print(f"   Агенты:     {label}  [{provider}]")
    print(f"   Синтезатор: {synth_info.get('label', synthesizer_model)}  [{synth_info.get('provider', '?')}]")

    if sequential and delay > 0:
        print(f"   Задержка между агентами: {delay}s")

    print(f"   Retry при 429: до {max_retries} попыток (exponential backoff)")

    if per_agent_models:
        print(f"   Переопределения агентов: {per_agent_models}")

    if provider == "lmstudio" or synth_info.get("provider") == "lmstudio":
        print(f"   LM Studio URL: {lmstudio_url}")
    print()

    # Финальный маппинг agent_key → model_key
    agent_model_map: dict[str, str] = {
        key: per_agent_models.get(key, model_key)
        for key in AGENT_DEFINITIONS
    }

    agent_results: list[AgentResult] = []

    def _run_one(agent_key: str, definition: dict) -> AgentResult:
        result = run_agent_sync(
            agent_key, definition,
            agent_model_map[agent_key],
            pitch_text, lmstudio_url,
            max_retries=max_retries,
        )
        icon = "✅" if not result.error else "❌"
        print(f"  {icon} {result.emoji} {result.agent_name:<22} {result.duration_ms:>5}ms  [{result.provider}]")

        return result

    if sequential:
        # ── Последовательный режим ──────────────────────────────────────────
        # Агенты запускаются строго один за другим.
        # delay между агентами снижает нагрузку на rate-limit окно (RPM/TPM).
        # _call_with_retry внутри каждого агента независимо обрабатывает 429.

        for i, (agent_key, definition) in enumerate(AGENT_DEFINITIONS.items()):
            agent_results.append(_run_one(agent_key, definition))

            if delay > 0 and i < len(AGENT_DEFINITIONS) - 1:
                print(f"   ⏸  пауза {delay}s...")
                time.sleep(delay)

    else:
        # ── Параллельный режим ──────────────────────────────────────────────
        # Все агенты стартуют одновременно. _call_with_retry в каждом потоке
        # независимо ждёт и повторяет при 429 — без блокировки других агентов.

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(_run_one, agent_key, definition): agent_key

                for agent_key, definition in AGENT_DEFINITIONS.items()
            }
            for future in concurrent.futures.as_completed(futures):
                agent_results.append(future.result())

    # Сортировка по исходному порядку конфига
    order = list(AGENT_DEFINITIONS.keys())
    agent_results.sort(key=lambda r: order.index(r.agent_key) if r.agent_key in order else 99)

    # Синтез
    print(f"\nСинтезатор [{synth_info.get('provider', '?')}]...")
    t0 = time.time()
    synthesis = run_synthesizer(agent_results, synthesizer_model, lmstudio_url, max_retries=max_retries)
    print(f"  ✅ Готово — {int((time.time() - t0) * 1000)}ms")

    total_ms = int((time.time() - total_start) * 1000)
    print(f"\nИтого: {total_ms / 1000:.1f}s\n")

    return CommitteeReport(
        pitch_excerpt=pitch_text[:300] + "...",
        model_key=model_key,
        sequential=sequential,
        agent_results=agent_results,
        synthesis=synthesis,
        total_duration_ms=total_ms,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )


# endregion


# region Генерация отчёта
def print_report(report: CommitteeReport):
    print("ОТЧЁТ ИНВЕСТИЦИОННОГО КОМИТЕТА")

    for ar in report.agent_results:
        print(f"{ar.emoji}  {ar.agent_name.upper()}  · {ar.model_used}  [{ar.provider}]")

        if ar.error:
            print(f"  ❌ {ar.error}")
        elif ar.parsed:
            score = ar.parsed.get("score", "N/A")
            rationale = ar.parsed.get("score_rationale", "")
            print(f"  Оценка: {score}/10 — {rationale}")

    if report.synthesis:
        s = report.synthesis
        rec = s.get("investment_recommendation", "unknown")
        labels = {
            "invest": "✅  МОЖНО ИНВЕСТИРОВАТЬ",
            "pass": "❌  НЕЛЬЗЯ ИНВЕСТИРОВАТЬ",
            "more_diligence": "🔄  НЕОБХОДИМА ДОРАБОТКА",
        }

        print("РЕШЕНИЕ КОМИТЕТА")
        print(f"\n  Рекомендация:      {labels.get(rec, rec)}")
        print(f"  Взвешенная оценка: {s.get('weighted_score', 'N/A')}/10")
        print(f"\n  Резюме:\n  {s.get('executive_summary', '')}")
        print(f"\n  Обоснование:\n  {s.get('recommendation_rationale', '')}")

        if s.get("critical_blockers"):
            print(f"\n  Блокеры: {', '.join(s['critical_blockers'])}")

        if s.get("next_steps"):
            print("\n  Следующие шаги:")
            for step in s["next_steps"]:
                print(f"    → {step}")


# endregion


# Пример питча для теста
SAMPLE_PITCH = """
    Стартап: AgroSense AI

    Проблема: 40% урожая в развивающихся странах теряется из-за несвоевременного
    обнаружения болезней растений. Фермеры узнают о проблеме слишком поздно.

    Решение: Мобильное приложение на основе computer vision. Фермер фотографирует
    листья растений — AI за 3 секунды определяет болезнь и даёт рекомендации
    по лечению. Работает офлайн (модель на устройстве).

    Рынок: TAM $85 млрд (мировой рынок агрострахования + средства защиты растений).
    Целевой сегмент — Индия, Бразилия, Нигерия. SAM $12 млрд.

    Бизнес-модель: Freemium. Базовая диагностика бесплатно, расширенные функции
    (история болезней, рекомендации удобрений, агроном онлайн) — $3/месяц.
    B2B: лицензии для агростраховых компаний — $50k+/год.

    Тракция: 45,000 активных пользователей в Индии (6 месяцев после запуска),
    NPS 71, 3 пилота с крупными страховыми компаниями.

    Команда: 
    - CEO: Priya Sharma, ex-Google AI, PhD Computer Vision, IIT Delhi
    - CTO: Marcus Oliveira, 8 лет в AgriTech, ex-Bayer Digital Farming
    - COO: Amara Osei, ex-Olam International, 10 лет операций в Африке

    Привлекаем: $3M Seed. Использование: 60% product, 25% GTM Индия+Нигерия, 15% ops.
    Runway: 24 месяца. Целевой ARR через 24м: $2.4M.
    """

# Точка входа
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AuditMate оценка стартапов (OpenRouter + LM Studio)",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL_KEY,
        help=(
            "Модель для всех агентов.\n"
            "Облако:  gptoss20b | gptoss120b | qwen3 | llama3.2.3 | llama3.3 | gemma3\n"
            "Локально: local | qwen2.5-3b | qwen2.5-7b | llama3.2-3b | phi3.5-mini | gemma3-4b\n"
            f"По умолчанию: {DEFAULT_MODEL_KEY}"
        ),
    )
    parser.add_argument(
        "--synthesizer-model", default=None,
        help=(
            "Модель синтезатора (если отличается от --model).\n"
            "Пример: --model local --synthesizer-model gptoss20b"
        ),
    )
    parser.add_argument(
        "--lmstudio-url", default=LMSTUDIO_BASE_URL,
        help=f"URL сервера LM Studio (по умолчанию: {LMSTUDIO_BASE_URL})",
    )
    parser.add_argument(
        "--pitch-file", default=None,
        help="Путь к .txt файлу с питчем (без флага — используется встроенный пример)",
    )
    parser.add_argument(
        "--output", default="committee_report.json",
        help="Путь для сохранения JSON-отчёта",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        default=None,
        help=(
            "Запускать агентов последовательно, по одному.\n"
            "Рекомендуется при использовании локальных моделей (экономит VRAM).\n"
            "Без флага: авто — локальная модель → sequential, облако → parallel."
        ),
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        default=False,
        help=(
            "Принудительно параллельный запуск даже для локальных моделей.\n"
            "Используй только если VRAM хватает на 4 одновременных запроса."
        ),
    )
    parser.add_argument(
        "--delay",
        type=float, default=0.0,
        help=(
            "Пауза в секундах между агентами в sequential-режиме.\n"
            "Помогает при мягких rate-limit окнах (например RPM=10).\n"
            "Пример: --sequential --delay 5  →  пауза 5с между каждым агентом.\n"
            "Игнорируется в параллельном режиме."
        ),
    )
    parser.add_argument(
        "--max-retries",
        type=int, default=3,
        dest="max_retries",
        help=(
            "Максимум повторов при ошибке 429 Rate Limit.\n"
            "Каждый агент и синтезатор повторяют независимо.\n"
            "Стратегия: exponential backoff + jitter (2s, 4s, 8s ...).\n"
            "Если API возвращает Retry-After — используется он.\n"
            "По умолчанию: 3"
        ),
    )
    parser.add_argument(
        "--list-models", action="store_true",
        help="Показать список доступных моделей и выйти",
    )

    args = parser.parse_args()

    if args.list_models:
        print_available_models()
        raise SystemExit(0)

    if args.sequential:
        sequential = True
    elif args.parallel:
        sequential = False
    else:
        sequential = None

    pitch = SAMPLE_PITCH
    if args.pitch_file:
        with open(args.pitch_file, encoding="utf-8") as f:
            pitch = f.read()

    report = evaluate_pitch(
        pitch_text=pitch,
        model_key=args.model,
        synthesizer_model=args.synthesizer_model,
        lmstudio_url=args.lmstudio_url,
        sequential=sequential,
        delay=args.delay,
        max_retries=args.max_retries,
    )

    print_report(report)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(asdict(report), f, ensure_ascii=False, indent=2)

    print(f"\nОтчёт сохранён: {args.output}")