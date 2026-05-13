import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from auditmate.providers.catalog import OPENROUTER_BASE_URL
from auditmate.utils.retry import call_with_retry


class OpenRouterProvider:
    """OpenAI-совместимая реализация провайдера для OpenRouter."""

    name = "openrouter"

    def __init__(self) -> None:
        """Создаёт клиент, используя OPENROUTER_API_KEY из окружения."""

        load_dotenv()
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise EnvironmentError("Переменная окружения OPENROUTER_API_KEY не задана.")

        self.client = OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)

    def generate(
        self,
        model_id: str,
        system: str,
        user: str,
        temperature: float,
        max_retries: int = 3,
        response_model: type[BaseModel] | None = None,
    ) -> str:
        """Генерирует сырой ответ модели, при необходимости запрашивая JSON Schema."""

        kwargs = build_request_kwargs(model_id, system, user, temperature, self.name, response_model)
        response = call_with_retry(self.client, kwargs, max_retries=max_retries)
        return response.choices[0].message.content.strip()


def build_request_kwargs(
    model_id: str,
    system: str,
    user: str,
    temperature: float,
    provider: str,
    response_model: type[BaseModel] | None = None,
) -> dict:
    """Собирает аргументы OpenAI-compatible chat completion для провайдера."""

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
        if response_model:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "strict": True,
                    "schema": response_model.model_json_schema(),
                },
            }

    return kwargs
