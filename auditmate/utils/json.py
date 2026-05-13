import json

from pydantic import BaseModel, ValidationError

try:
    from json_repair import repair_json
except ImportError:  # pragma: no cover - зависимость объявлена, импорт остаётся мягким.
    repair_json = None


def strip_json(text: str) -> str:
    """Удаляет типичные markdown-обёртки вокруг JSON, сгенерированного моделью."""

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


def parse_json_response(raw: str) -> dict:
    """Парсит сырой ответ LLM как обычный JSON-объект."""

    return json.loads(strip_json(raw))


def parse_llm_json(raw: str, schema: type[BaseModel], debug_recorder=None, debug_name: str = "") -> BaseModel:
    """Валидирует JSON модели через Pydantic, один раз чиня повреждённый JSON."""

    payload = strip_json(raw)

    try:
        return schema.model_validate_json(payload)
    except ValidationError:
        if repair_json is None:
            raise

    repaired = repair_json(payload)
    if debug_recorder and debug_name:
        debug_recorder.save_repaired_json(debug_name, repaired)

    return schema.model_validate_json(repaired)
