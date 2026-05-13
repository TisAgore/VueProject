from typing import Protocol

from pydantic import BaseModel


class BaseProvider(Protocol):
    name: str

    def generate(
        self,
        model_id: str,
        system: str,
        user: str,
        temperature: float,
        max_retries: int = 3,
        response_model: type[BaseModel] | None = None,
    ) -> str:
        ...
