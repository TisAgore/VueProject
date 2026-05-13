import concurrent.futures
import time
from pathlib import Path
from typing import Optional

from auditmate.agents.definitions import AGENT_DEFINITIONS
from auditmate.agents.runner import run_agent_sync, run_synthesizer
from auditmate.core.context_builder import ContextBuilder, UnifiedContext
from auditmate.models.reports import AgentResult, CommitteeReport
from auditmate.providers.catalog import ALL_MODELS, DEFAULT_MODEL_KEY, LMSTUDIO_BASE_URL, is_local
from auditmate.tools.images.gemini_vision import enrich_image_attachments
from auditmate.tools.parsers import parse_attachments
from auditmate.utils.debug import DebugRecorder


def evaluate_pitch(
    pitch_text: str,
    attachment_paths: Optional[list[str | Path]] = None,
    unified_context: Optional[UnifiedContext] = None,
    model_key: str = DEFAULT_MODEL_KEY,
    synthesizer_model: Optional[str] = None,
    per_agent_models: Optional[dict[str, str]] = None,
    lmstudio_url: str = LMSTUDIO_BASE_URL,
    sequential: Optional[bool] = None,
    delay: float = 0.0,
    max_retries: int = 3,
    debug: bool = False,
    debug_dir: str | Path = ".auditmate_debug",
) -> CommitteeReport:
    """Запускает полный пайплайн инвестиционного комитета для питча и вложений."""

    per_agent_models = per_agent_models or {}
    synthesizer_model = synthesizer_model or model_key
    debug_recorder = DebugRecorder(enabled=debug, output_dir=debug_dir)
    parsed_attachments = parse_attachments(attachment_paths or [])
    parsed_attachments = enrich_image_attachments(parsed_attachments, debug_recorder=debug_recorder)
    context = unified_context or ContextBuilder().build(pitch_text, parsed_attachments)
    agent_context_text = context.to_prompt_text() or pitch_text
    debug_recorder.save_json("context.json", context)

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

    print(f"   Retry при 429: до {max_retries} попыток")

    if per_agent_models:
        print(f"   Переопределения агентов: {per_agent_models}")

    if parsed_attachments:
        print(f"   Attachments: {len(parsed_attachments)}")

    if provider == "lmstudio" or synth_info.get("provider") == "lmstudio":
        print(f"   LM Studio URL: {lmstudio_url}")
    print()

    agent_model_map: dict[str, str] = {
        key: per_agent_models.get(key, model_key)
        for key in AGENT_DEFINITIONS
    }

    agent_results: list[AgentResult] = []

    def _run_one(agent_key: str) -> AgentResult:
        definition = AGENT_DEFINITIONS[agent_key]
        result = run_agent_sync(
            agent_key,
            definition,
            agent_model_map[agent_key],
            agent_context_text,
            lmstudio_url,
            max_retries=max_retries,
            debug_recorder=debug_recorder,
        )
        icon = "OK" if not result.error else "ERR"
        print(f"  {icon} {result.emoji} {result.agent_name:<22} {result.duration_ms:>5}ms  [{result.provider}]")
        return result

    if sequential:
        for i, agent_key in enumerate(AGENT_DEFINITIONS):
            agent_results.append(_run_one(agent_key))
            if delay > 0 and i < len(AGENT_DEFINITIONS) - 1:
                print(f"   pause {delay}s...")
                time.sleep(delay)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(_run_one, agent_key): agent_key
                for agent_key in AGENT_DEFINITIONS
            }
            for future in concurrent.futures.as_completed(futures):
                agent_results.append(future.result())

    order = list(AGENT_DEFINITIONS.keys())
    agent_results.sort(key=lambda r: order.index(r.agent_key) if r.agent_key in order else 99)

    print(f"\nСинтезатор [{synth_info.get('provider', '?')}]...")
    t0 = time.time()
    synthesis = run_synthesizer(
        agent_results,
        synthesizer_model,
        lmstudio_url,
        max_retries=max_retries,
        debug_recorder=debug_recorder,
    )
    print(f"  Готово - {int((time.time() - t0) * 1000)}ms")

    total_ms = int((time.time() - total_start) * 1000)
    print(f"\nИтого: {total_ms / 1000:.1f}s\n")

    report = CommitteeReport(
        pitch_excerpt=agent_context_text[:300] + "...",
        model_key=model_key,
        sequential=sequential,
        agent_results=agent_results,
        synthesis=synthesis,
        total_duration_ms=total_ms,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
    debug_recorder.save_json("report.json", report)
    return report
