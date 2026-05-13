from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


AttachmentKind = Literal["text", "markdown", "json", "csv", "xlsx", "pdf", "docx", "image", "unknown"]


@dataclass(frozen=True)
class Attachment:
    """Описывает пользовательский файл до парсинга."""

    path: Path
    kind: AttachmentKind


@dataclass
class ParsedAttachment:
    """Хранит нормализованное содержимое, извлечённое из пользовательского файла."""

    attachment: Attachment
    text: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


def detect_attachment_kind(path: str | Path) -> AttachmentKind:
    """Определяет тип вложения по расширению файла."""

    suffix = Path(path).suffix.lower()
    if suffix == ".txt":
        return "text"
    if suffix == ".md":
        return "markdown"
    if suffix == ".json":
        return "json"
    if suffix == ".csv":
        return "csv"
    if suffix in {".xlsx", ".xls"}:
        return "xlsx"
    if suffix == ".pdf":
        return "pdf"
    if suffix == ".docx":
        return "docx"
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"}:
        return "image"

    return "unknown"


def create_attachment(path: str | Path) -> Attachment:
    """Создаёт объект Attachment с нормализованным путём и определённым типом."""

    normalized_path = Path(path).expanduser()
    return Attachment(path=normalized_path, kind=detect_attachment_kind(normalized_path))
