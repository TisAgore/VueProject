from openai import OpenAI
from pydantic import BaseModel

from auditmate.providers.catalog import LMSTUDIO_BASE_URL
from auditmate.providers.openrouter import build_request_kwargs
from auditmate.utils.retry import call_with_retry


class LMStudioProvider:
    """OpenAI-совместимая реализация провайдера для локального сервера LM Studio."""

    name = "lmstudio"

    def __init__(self, base_url: str = LMSTUDIO_BASE_URL) -> None:
        """Создаёт локальный клиент для настроенного base URL LM Studio."""

        self.base_url = base_url
        self.client = OpenAI(api_key="lm-studio", base_url=base_url)

    def generate(
        self,
        model_id: str,
        system: str,
        user: str,
        temperature: float,
        max_retries: int = 3,
        response_model: type[BaseModel] | None = None,
    ) -> str:
        """Генерирует сырой ответ модели через LM Studio."""

        kwargs = build_request_kwargs(model_id, system, user, temperature, self.name, response_model)
        response = call_with_retry(self.client, kwargs, max_retries=max_retries)
        return response.choices[0].message.content.strip()
