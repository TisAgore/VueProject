import base64
from pathlib import Path

from auditmate.models.attachments import Attachment, ParsedAttachment, create_attachment


class PDFParserTool:
    name = "parse_pdf"
    description = "Извлекает текст, страницы и metadata из PDF-файлов."

    def execute(self, input_data: Attachment | str | Path) -> ParsedAttachment:
        """Парсит PDF-файл через PyMuPDF."""

        import fitz

        attachment = _coerce_attachment(input_data)

        document = fitz.open(str(attachment.path))
        try:
            pages = []
            for page_index, page in enumerate(document, start=1):
                text = page.get_text("text").strip()
                pages.append(
                    {
                        "page": page_index,
                        "text": text,
                        "characters": len(text),
                    }
                )

            image_based = len("".join(page["text"] for page in pages).strip()) == 0
            page_images = _render_pdf_pages(document) if image_based else []
            image_page_numbers = _find_pages_with_embedded_images(document)
            image_page_previews = _render_pdf_pages(document, page_numbers=image_page_numbers)

            combined_text = "\n\n".join(
                f"[Страница {page['page']}]\n{page['text']}"
                for page in pages
                if page["text"]
            )
            metadata = dict(document.metadata or {})
            metadata.update(
                {
                    "source": str(attachment.path),
                    "kind": attachment.kind,
                    "pages": document.page_count,
                    "characters": len(combined_text),
                    "image_based": image_based,
                }
            )

            return ParsedAttachment(
                attachment=attachment,
                text=combined_text,
                data={
                    "pages": pages,
                    "pdf_metadata": dict(document.metadata or {}),
                    "image_based": metadata["image_based"],
                    "page_images": page_images,
                    "image_page_numbers": image_page_numbers,
                    "image_page_previews": image_page_previews,
                },
                metadata=metadata,
            )
        finally:
            document.close()


def _render_pdf_pages(
    document,
    page_numbers: list[int] | None = None,
) -> list[dict[str, str | int]]:
    """Рендерит страницы PDF в PNG base64 для последующего vision-анализа."""

    selected_pages = set(page_numbers or [])
    page_images = []
    for page_index, page in enumerate(document, start=1):
        if page_numbers is not None and page_index not in selected_pages:
            continue
        pixmap = page.get_pixmap(matrix=_build_render_matrix())
        png_bytes = pixmap.tobytes("png")
        page_images.append(
            {
                "page": page_index,
                "mime_type": "image/png",
                "base64": base64.b64encode(png_bytes).decode("ascii"),
            }
        )

    return page_images


def _find_pages_with_embedded_images(document) -> list[int]:
    """Возвращает номера страниц, содержащих встроенные растровые изображения."""

    pages = []
    for page_index, page in enumerate(document, start=1):
        blocks = page.get_text("dict").get("blocks", [])
        if any(block.get("type") == 1 for block in blocks):
            pages.append(page_index)

    return pages


def _build_render_matrix():
    """Создаёт матрицу рендера страниц с умеренным upscale для OCR/vision."""

    import fitz

    return fitz.Matrix(2, 2)


def _coerce_attachment(input_data: Attachment | str | Path) -> Attachment:
    """Нормализует вход парсера в объект Attachment."""

    if isinstance(input_data, Attachment):
        return input_data

    return create_attachment(input_data)
