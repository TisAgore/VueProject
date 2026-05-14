LMSTUDIO_BASE_URL = "http://localhost:1234/v1"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

CLOUD_MODELS: dict[str, dict] = {
    "auto": {
        "id": "openrouter/auto",
        "label": "OpenRouter Auto",
        "provider": "openrouter",
    },
    "gemini-3.1-flash-lite": {
        "id": "gemini-3.1-flash-lite",
        "label": "Gemini 3.1 Flash Lite",
        "provider": "gemini"
    },
    "gemini-3-flash-preview": {
        "id": "gemini-3-flash-preview",
        "label": "Gemini 3 Flash Preview",
        "provider": "gemini"
    },
    "gemini-2.5-flash": {
        "id": "gemini-2.5-flash",
        "label": "Gemini 2.5 Flash",
        "provider": "gemini"
    },
    "gemini-2.5-flash-lite": {
        "id": "gemini-2.5-flash-lite",
        "label": "Gemini 2.5 Flash Lite",
        "provider": "gemini"
    },
    "gemma-4-31b-it": {
        "id": "gemma-4-31b-it",
        "label": "Gemma 4 31B IT",
        "provider": "gemini"
    },
    "gemma-4-26b-a4b-it": {
        "id": "gemma-4-26b-a4b-it",
        "label": "Gemma 4 26B IT",
        "provider": "gemini"
    }
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
DEFAULT_MODEL_KEY = "auto"


def resolve_model_id(model_key: str) -> str:
    """Преобразует удобный ключ модели в model id для провайдера."""

    if model_key in ALL_MODELS:
        model_id = ALL_MODELS[model_key]["id"]
        return "" if model_id == "auto" else model_id

    return model_key


def is_local(model_key: str) -> bool:
    """Возвращает True, если ключ модели обслуживается через LM Studio."""

    return ALL_MODELS.get(model_key, {}).get("provider") == "lmstudio"


def provider_for_model(model_key: str) -> str:
    """Возвращает имя провайдера для ключа модели, по умолчанию OpenRouter."""

    return ALL_MODELS.get(model_key, {}).get("provider", "openrouter")


def print_available_models() -> None:
    """Печатает каталог моделей, доступный из CLI."""

    print("\nОблачные модели (OpenRouter):")
    for key, info in CLOUD_MODELS.items():
        print(f"  {key:<14} - {info['label']}")

    print("\nЛокальные модели (LM Studio):")
    for key, info in LOCAL_MODELS.items():
        note = info.get("note", "")
        print(f"  {key:<14} - {info['label']}")
        if note:
            print(f"  {'':14}   -> {note}")

    print()
