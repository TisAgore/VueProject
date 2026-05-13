import json
import os
from pathlib import Path
from urllib import error, request

from dotenv import load_dotenv

from auditmate.models.attachments import ParsedAttachment
from auditmate.utils.debug import DebugRecorder


GEMINI_VISION_MODEL = "gemini-2.5-flash-lite"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def enrich_image_attachments(
    attachments: list[ParsedAttachment],
    debug_recorder: DebugRecorder | None = None,
    model: str = GEMINI_VISION_MODEL,
) -> list[ParsedAttachment]:
    """Дополняет image-вложения и сканированные PDF описанием через Gemini."""

    load_dotenv()
    if not os.getenv("GOOGLE_AI_API_KEY"):
        return attachments

    enriched: list[ParsedAttachment] = []
    for attachment in attachments:
        if attachment.attachment.kind == "image":
            enriched.append(_enrich_single_image_attachment(attachment, debug_recorder=debug_recorder, model=model))
            continue

        if attachment.attachment.kind == "pdf" and attachment.data.get("image_based"):
            enriched.append(
                _enrich_pdf_attachment(
                    attachment,
                    page_images=attachment.data.get("page_images", []),
                    heading="Описание сканированного PDF",
                    debug_recorder=debug_recorder,
                    model=model,
                )
            )
            continue

        if attachment.attachment.kind == "pdf" and attachment.data.get("image_page_previews"):
            enriched.append(
                _enrich_pdf_attachment(
                    attachment,
                    page_images=attachment.data.get("image_page_previews", []),
                    heading="Визуальное описание PDF",
                    debug_recorder=debug_recorder,
                    model=model,
                )
            )
            continue

        enriched.append(attachment)

    return enriched


def _enrich_single_image_attachment(
    attachment: ParsedAttachment,
    debug_recorder: DebugRecorder | None = None,
    model: str = GEMINI_VISION_MODEL,
) -> ParsedAttachment:
    """Дополняет одно image-вложение текстовым описанием Gemini."""

    try:
        description = describe_image_attachment(attachment, model=model, debug_recorder=debug_recorder)
    except Exception as exc:
        attachment.data["image_description_error"] = str(exc)
        return attachment

    attachment.data["image_description"] = description
    attachment.text = f"{attachment.text}\n\n[Описание изображения]\n{description}".strip()
    return attachment


def _enrich_pdf_attachment(
    attachment: ParsedAttachment,
    page_images: list[dict[str, str | int]],
    heading: str,
    debug_recorder: DebugRecorder | None = None,
    model: str = GEMINI_VISION_MODEL,
) -> ParsedAttachment:
    """Дополняет PDF описаниями страниц через Gemini."""

    if not page_images:
        attachment.data["image_description_error"] = "Для PDF отсутствуют отрендеренные страницы."
        return attachment

    page_descriptions: list[dict[str, str | int]] = []
    for page_image in page_images:
        page_number = int(page_image["page"])
        page_attachment = ParsedAttachment(
            attachment=attachment.attachment,
            text="",
            data={
                "mime_type": page_image["mime_type"],
                "base64": page_image["base64"],
            },
            metadata={"page": page_number},
        )

        try:
            description = describe_image_attachment(
                page_attachment,
                model=model,
                debug_recorder=debug_recorder,
                debug_name=f"{attachment.attachment.path.stem}.page_{page_number}",
            )
        except Exception as exc:
            page_descriptions.append({"page": page_number, "description": "", "error": str(exc)})
            continue

        page_descriptions.append({"page": page_number, "description": description})

    successful = [item for item in page_descriptions if item.get("description")]
    if successful:
        summary_lines = [
            f"Страница {item['page']}: {item['description']}"
            for item in successful
        ]
        summary = "\n\n".join(summary_lines)
        attachment.data["image_description"] = summary
        attachment.data["page_descriptions"] = page_descriptions
        attachment.data["pdf_visual_summary"] = summary
        attachment.text = (
            f"{attachment.text}\n\n[{heading}]\n{summary}".strip()
            if attachment.text
            else f"[{heading}]\n{summary}"
        )
    else:
        errors = [item.get("error", "unknown error") for item in page_descriptions]
        attachment.data["image_description_error"] = "; ".join(errors)

    return attachment


def describe_image_attachment(
    attachment: ParsedAttachment,
    model: str = GEMINI_VISION_MODEL,
    debug_recorder: DebugRecorder | None = None,
    debug_name: str = "",
) -> str:
    """Получает краткое структурированное описание изображения через Gemini."""

    load_dotenv()
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key:
        raise RuntimeError("Переменная окружения GOOGLE_AI_API_KEY не задана.")

    mime_type = attachment.data.get("mime_type", "application/octet-stream")
    image_b64 = attachment.data.get("base64")
    if not image_b64:
        raise ValueError("Во вложении отсутствует base64-представление изображения.")

    prompt = (
        "Опиши изображение для инвестиционного анализа стартапа. "
        "Ответь на русском языке компактно и структурированно.\n"
        "Нужно:\n"
        "1. Что изображено.\n"
        "2. Какой текст/KPI/метрики видны.\n"
        "3. Какие выводы важны для due diligence.\n"
        "4. Что на изображении неразборчиво или вызывает сомнения."
    )

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": image_b64,
                        }
                    },
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.8,
            "maxOutputTokens": 500,
        },
    }

    artifact_name = debug_name or _safe_stem(attachment.attachment.path)

    if debug_recorder:
        debug_recorder.save_json(
            f"prompts/{artifact_name}.gemini_image_request.json",
            payload,
        )

    url = f"{GEMINI_API_BASE}/{model}:generateContent?key={api_key}"
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=60) as response:
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini vision HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Gemini vision network error: {exc.reason}") from exc

    if debug_recorder:
        debug_recorder.save_text(
            f"responses/{artifact_name}.gemini_image_response.json",
            body,
        )

    data = json.loads(body)
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"Gemini не вернул candidates: {body}")

    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [part.get("text", "").strip() for part in parts if part.get("text")]
    description = "\n".join(part for part in text_parts if part).strip()
    if not description:
        raise RuntimeError(f"Gemini не вернул текстовое описание: {body}")

    return description


def _safe_stem(path: Path) -> str:
    """Преобразует имя файла в безопасный stem для debug-артефактов."""

    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in path.stem) or "image"
