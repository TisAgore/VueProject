from auditmate.providers.catalog import provider_for_model
from auditmate.providers.lmstudio import LMStudioProvider
from auditmate.providers.openrouter import OpenRouterProvider
from auditmate.providers.gemini import GeminiProvider


def get_provider_for_model(model_key: str, lmstudio_url: str = ""):
    """Создаёт провайдера, соответствующего выбранному ключу модели."""

    provider = provider_for_model(model_key)
    if provider == "lmstudio":
        return LMStudioProvider(lmstudio_url) if lmstudio_url else LMStudioProvider()
    if provider == 'gemini':
        return GeminiProvider()

    return OpenRouterProvider()
