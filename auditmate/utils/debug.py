import json
import re
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


class DebugRecorder:
    """Сохраняет контекст, prompts и ответы моделей для отладки пайплайна."""

    def __init__(self, enabled: bool = False, output_dir: str | Path = ".auditmate_debug") -> None:
        """Создаёт recorder и директории для debug-артефактов."""

        self.enabled = enabled
        self.output_dir = Path(output_dir)
        self.run_dir: Path | None = None

        if self.enabled:
            timestamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
            self.run_dir = self.output_dir / timestamp
            for name in ("prompts", "responses", "repaired_json"):
                (self.run_dir / name).mkdir(parents=True, exist_ok=True)

    def save_json(self, relative_path: str, data: Any) -> None:
        """Сохраняет JSON-файл внутри директории текущего debug-запуска."""

        if not self.enabled or not self.run_dir:
            return

        path = self.run_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(_to_jsonable(data), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def save_text(self, relative_path: str, text: str) -> None:
        """Сохраняет текстовый файл внутри директории текущего debug-запуска."""

        if not self.enabled or not self.run_dir:
            return

        path = self.run_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def save_prompt(self, name: str, system: str, user: str) -> None:
        """Сохраняет system/user prompt для агента или синтезатора."""

        safe_name = _safe_name(name)
        self.save_text(f"prompts/{safe_name}.system.txt", system)
        self.save_text(f"prompts/{safe_name}.user.txt", user)

    def save_response(self, name: str, raw_response: str) -> None:
        """Сохраняет сырой ответ модели."""

        self.save_text(f"responses/{_safe_name(name)}.txt", raw_response)

    def save_repaired_json(self, name: str, repaired_json: str) -> None:
        """Сохраняет JSON после repair-слоя."""

        self.save_text(f"repaired_json/{_safe_name(name)}.json", repaired_json)


def _safe_name(name: str) -> str:
    """Приводит произвольное имя к безопасному имени файла."""

    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", name).strip("_") or "item"


def _to_jsonable(data: Any) -> Any:
    """Преобразует dataclass/Pydantic/Path объекты в JSON-совместимые структуры."""

    if is_dataclass(data):
        return _to_jsonable(asdict(data))
    if hasattr(data, "model_dump"):
        return _to_jsonable(data.model_dump())
    if isinstance(data, Path):
        return str(data)
    if isinstance(data, dict):
        return {str(key): _to_jsonable(value) for key, value in data.items()}
    if isinstance(data, list):
        return [_to_jsonable(item) for item in data]
    if isinstance(data, tuple):
        return [_to_jsonable(item) for item in data]

    return data
