import json
import time

from pydantic import ValidationError

from auditmate.agents.definitions import AgentDefinition, SYNTHESIZER_SYSTEM
from auditmate.models.reports import AgentResult
from auditmate.models.responses import SynthesisResponse
from auditmate.providers.catalog import provider_for_model, resolve_model_id
from auditmate.providers.factory import get_provider_for_model
from auditmate.utils.json import parse_llm_json


def run_agent_sync(
    agent_key: str,
    definition: AgentDefinition,
    model_key: str,
    pitch_text: str,
    lmstudio_url: str,
    max_retries: int = 3,
    debug_recorder=None,
) -> AgentResult:
    """Запускает одного специализированного агента и валидирует его структурированный ответ."""

    model_id = resolve_model_id(model_key)
    provider_name = provider_for_model(model_key)
    start = time.time()

    try:
        provider = get_provider_for_model(model_key, lmstudio_url)
        user_msg = f"Проанализируй питч-дек стартапа:\n\n---\n{pitch_text}\n---"
        if debug_recorder:
            debug_recorder.save_prompt(agent_key, definition.system_prompt, user_msg)

        raw = provider.generate(
            model_id=model_id,
            system=definition.system_prompt,
            user=user_msg,
            temperature=definition.temperature,
            max_retries=max_retries,
            response_model=definition.response_model,
        )
        if debug_recorder:
            debug_recorder.save_response(agent_key, raw)

        try:
            parsed = parse_llm_json(raw, definition.response_model, debug_recorder, agent_key).model_dump()
        except (json.JSONDecodeError, ValidationError) as e:
            return AgentResult(
                agent_key=agent_key,
                agent_name=definition.name,
                emoji=definition.emoji,
                model_used=model_id or "auto",
                provider=provider_name,
                raw_response=raw,
                parsed=None,
                duration_ms=int((time.time() - start) * 1000),
                error=f"JSON parse error: {e}",
            )

        return AgentResult(
            agent_key=agent_key,
            agent_name=definition.name,
            emoji=definition.emoji,
            model_used=model_id or "auto",
            provider=provider_name,
            raw_response=raw,
            parsed=parsed,
            duration_ms=int((time.time() - start) * 1000),
        )

    except Exception as e:
        err = str(e)
        if provider_name == "lmstudio" and ("Connection refused" in err or "connect" in err.lower()):
            err = (
                "Не удалось подключиться к LM Studio.\n"
                "  1. Открой LM Studio -> вкладка 'Local Server'\n"
                "  2. Загрузи модель (например Qwen2.5 3B Instruct Q4_K_M)\n"
                "  3. Нажми 'Start Server' (порт 1234)\n"
                f"  URL: {lmstudio_url}"
            )

        return AgentResult(
            agent_key=agent_key,
            agent_name=definition.name,
            emoji=definition.emoji,
            model_used=model_id or "auto",
            provider=provider_name,
            raw_response="",
            parsed=None,
            duration_ms=int((time.time() - start) * 1000),
            error=err,
        )


def run_synthesizer(
    agent_results: list[AgentResult],
    synthesizer_model: str,
    lmstudio_url: str,
    max_retries: int = 3,
    debug_recorder=None,
) -> dict | None:
    """Объединяет успешные ответы агентов в итоговое решение комитета."""

    reports = {
        ar.agent_key: {"name": ar.agent_name, "report": ar.parsed}
        for ar in agent_results
        if ar.parsed
    }

    if not reports:
        print("  Нет успешных отчётов агентов - синтез невозможен.")
        return None

    provider_name = provider_for_model(synthesizer_model)
    model_id = resolve_model_id(synthesizer_model)
    provider = get_provider_for_model(synthesizer_model, lmstudio_url)
    user_msg = (
        f"Отчёты аналитиков:\n"
        f"{json.dumps(reports, ensure_ascii=False, indent=2)}\n\n"
        f"Создай итоговое инвестиционное заключение комитета."
    )
    if debug_recorder:
        debug_recorder.save_prompt("synthesizer", SYNTHESIZER_SYSTEM, user_msg)

    try:
        raw = provider.generate(
            model_id=model_id,
            system=SYNTHESIZER_SYSTEM,
            user=user_msg,
            temperature=0.3,
            max_retries=max_retries,
            response_model=SynthesisResponse,
        )
        if debug_recorder:
            debug_recorder.save_response("synthesizer", raw)

        return parse_llm_json(raw, SynthesisResponse, debug_recorder, "synthesizer").model_dump()
    except Exception as e:
        print(f"  Synthesizer error [{provider_name}]: {e}")
        return None
