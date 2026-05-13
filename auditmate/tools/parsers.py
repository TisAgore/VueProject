import json
from pathlib import Path
from typing import Any

from auditmate.models.attachments import Attachment, ParsedAttachment, create_attachment
from auditmate.tools.base import BaseTool
from auditmate.tools.documents.docx_parser import DOCXParserTool
from auditmate.tools.documents.pdf_parser import PDFParserTool
from auditmate.tools.images.image_parser import ImageParserTool
from auditmate.tools.spreadsheets.table_parser import CSVParserTool, XLSXParserTool


class AttachmentParserError(ValueError):
    """Возникает, когда текущий набор парсеров не поддерживает вложение."""


class TextParserTool:
    name = "parse_text"
    description = "Читает обычный текст или markdown в нормализованное текстовое содержимое."

    def execute(self, input_data: Attachment | str | Path) -> ParsedAttachment:
        """Парсит .txt или .md файл в ParsedAttachment."""

        attachment = _coerce_attachment(input_data)
        text = attachment.path.read_text(encoding="utf-8")
        return ParsedAttachment(
            attachment=attachment,
            text=text,
            metadata={
                "source": str(attachment.path),
                "kind": attachment.kind,
                "characters": len(text),
            },
        )


class JSONParserTool:
    name = "parse_json"
    description = "Читает JSON-файлы как структурированные данные и человекочитаемый текст."

    def execute(self, input_data: Attachment | str | Path) -> ParsedAttachment:
        """Парсит .json файл в структурированные данные и форматированный текст."""

        attachment = _coerce_attachment(input_data)
        with attachment.path.open(encoding="utf-8") as f:
            data = json.load(f)

        text = json.dumps(data, ensure_ascii=False, indent=2)
        return ParsedAttachment(
            attachment=attachment,
            text=text,
            data={"json": data},
            metadata={
                "source": str(attachment.path),
                "kind": attachment.kind,
                "characters": len(text),
            },
        )


def parse_attachment(path: str | Path) -> ParsedAttachment:
    """Парсит поддерживаемый файл через встроенный набор парсеров."""

    attachment = create_attachment(path)

    if not attachment.path.exists():
        raise FileNotFoundError(f"Attachment not found: {attachment.path}")

    if attachment.kind in {"text", "markdown"}:
        return TextParserTool().execute(attachment)
    if attachment.kind == "json":
        return JSONParserTool().execute(attachment)
    if attachment.kind == "csv":
        return CSVParserTool().execute(attachment)
    if attachment.kind == "xlsx":
        return XLSXParserTool().execute(attachment)
    if attachment.kind == "pdf":
        return PDFParserTool().execute(attachment)
    if attachment.kind == "docx":
        return DOCXParserTool().execute(attachment)
    if attachment.kind == "image":
        return ImageParserTool().execute(attachment)

    raise AttachmentParserError(f"Unsupported attachment type: {attachment.path.suffix}")


def parse_attachments(paths: list[str | Path]) -> list[ParsedAttachment]:
    """Парсит все поддерживаемые файлы в порядке, заданном пользователем."""

    return [parse_attachment(path) for path in paths]


def _coerce_attachment(input_data: Attachment | str | Path) -> Attachment:
    """Нормализует вход парсера в объект Attachment."""

    if isinstance(input_data, Attachment):
        return input_data

    return create_attachment(input_data)


BUILTIN_PARSERS: list[BaseTool] = [
    TextParserTool(),
    JSONParserTool(),
    CSVParserTool(),
    XLSXParserTool(),
    PDFParserTool(),
    DOCXParserTool(),
    ImageParserTool(),
]
