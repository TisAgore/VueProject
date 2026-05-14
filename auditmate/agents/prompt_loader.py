from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(name: str) -> str:
    """Загружает промпт из файла."""
    path = PROMPTS_DIR / f"{name}.txt"
    return path.read_text(encoding="utf-8").strip()