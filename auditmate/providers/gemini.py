import os

from google import genai
from google.genai import types
from dotenv import load_dotenv
from pydantic import BaseModel

from auditmate.utils.retry import call_with_retry


class GeminiProvider:
    """Реализация провайдера для Gemini"""
    name = "gemini"

    def __init__(self) -> None:
        """Создаёт клиент, используя GOOGLE_AI_API_KEY из окружения. """
        load_dotenv()

        api_key = os.getenv("GOOGLE_AI_API_KEY")
        if not api_key:
            raise ValueError("Переменная окружения GOOGLE_AI_API_KEY не задана.")

        self.client = genai.Client(api_key=api_key)

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

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system,
        )

        if response_model:
            config.response_mime_type = "application/json"
            config.response_schema = response_model

        response = call_with_retry(
            lambda: self.client.models.generate_content(
                model=model_id,
                contents=user,
                config=config,
            ),
            max_retries=max_retries,
        )

        return response.text.strip()