import base64
import mimetypes
from pathlib import Path

from auditmate.models.attachments import Attachment, ParsedAttachment, create_attachment


class ImageParserTool:
    name = "parse_image"
    description = "Собирает metadata изображения и готовит данные для vision-провайдера."

    def execute(self, input_data: Attachment | str | Path) -> ParsedAttachment:
        """Парсит изображение без визуального анализа содержимого."""

        from PIL import Image

        attachment = _coerce_attachment(input_data)

        mime_type = mimetypes.guess_type(attachment.path)[0] or "application/octet-stream"
        with Image.open(attachment.path) as image:
            width, height = image.size
            mode = image.mode
            format_name = image.format

        binary = attachment.path.read_bytes()
        text = (
            f"[Изображение: {attachment.path.name}]\n"
            f"MIME: {mime_type}\n"
            f"Размер: {width}x{height}\n"
            f"Формат: {format_name}\n"
            "Визуальное содержание не анализировалось локально; "
            "для этого нужен multimodal provider."
        )

        return ParsedAttachment(
            attachment=attachment,
            text=text,
            data={
                "mime_type": mime_type,
                "width": width,
                "height": height,
                "mode": mode,
                "format": format_name,
                "base64": base64.b64encode(binary).decode("ascii"),
            },
            metadata={
                "source": str(attachment.path),
                "kind": attachment.kind,
                "mime_type": mime_type,
                "width": width,
                "height": height,
                "bytes": len(binary),
            },
        )


def _coerce_attachment(input_data: Attachment | str | Path) -> Attachment:
    """Нормализует вход парсера в объект Attachment."""

    if isinstance(input_data, Attachment):
        return input_data

    return create_attachment(input_data)

