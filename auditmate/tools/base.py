from typing import Any, Protocol


class BaseTool(Protocol):
    """Минимальный протокол для внутренних MCP-lite инструментов."""

    name: str
    description: str

    def execute(self, input_data: Any) -> Any:
        """Запускает инструмент с уже нормализованными входными данными."""

        ...
