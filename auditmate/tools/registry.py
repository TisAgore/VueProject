from auditmate.tools.base import BaseTool

TOOLS: dict[str, BaseTool] = {}


def register_tool(tool: BaseTool) -> None:
    """Регистрирует экземпляр инструмента по его публичному имени."""

    TOOLS[tool.name] = tool


def get_tool(name: str) -> BaseTool:
    """Возвращает зарегистрированный инструмент по имени."""

    return TOOLS[name]


def list_tools() -> list[str]:
    """Возвращает имена зарегистрированных инструментов в детерминированном порядке."""

    return sorted(TOOLS)


def register_builtin_tools() -> None:
    """Регистрирует инструменты-парсеры, поставляемые вместе с AuditMate."""

    from auditmate.tools.parsers import BUILTIN_PARSERS

    for tool in BUILTIN_PARSERS:
        register_tool(tool)
