import json

from auditmate.models.attachments import create_attachment, ParsedAttachment
from auditmate.tools.images.gemini_vision import describe_image_attachment, enrich_image_attachments


class _FakeHTTPResponse:
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_describe_image_attachment_parses_gemini_response(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "test-key")

    def fake_urlopen(req, timeout=60):
        return _FakeHTTPResponse(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "На изображении график роста выручки."}
                            ]
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("auditmate.tools.images.gemini_vision.request.urlopen", fake_urlopen)

    path = tmp_path / "chart.png"
    path.write_bytes(b"fake")
    parsed = ParsedAttachment(
        attachment=create_attachment(path),
        text="",
        data={"mime_type": "image/png", "base64": "ZmFrZQ=="},
        metadata={},
    )

    description = describe_image_attachment(parsed)

    assert "график роста выручки" in description


def test_enrich_image_attachments_adds_description(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "test-key")
    monkeypatch.setattr(
        "auditmate.tools.images.gemini_vision.describe_image_attachment",
        lambda attachment, model="gemini-2.5-flash-lite", debug_recorder=None, debug_name="": "Описание изображения",
    )

    path = tmp_path / "chart.png"
    path.write_bytes(b"fake")
    parsed = ParsedAttachment(
        attachment=create_attachment(path),
        text="[Изображение]",
        data={"mime_type": "image/png", "base64": "ZmFrZQ=="},
        metadata={},
    )

    enriched = enrich_image_attachments([parsed])

    assert enriched[0].data["image_description"] == "Описание изображения"
    assert "[Описание изображения]" in enriched[0].text


def test_enrich_image_based_pdf_adds_page_descriptions(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "test-key")
    monkeypatch.setattr(
        "auditmate.tools.images.gemini_vision.describe_image_attachment",
        lambda attachment, model="gemini-2.5-flash-lite", debug_recorder=None, debug_name="": "На странице виден график ARR.",
    )

    path = tmp_path / "scan.pdf"
    path.write_bytes(b"fake")
    parsed = ParsedAttachment(
        attachment=create_attachment(path),
        text="",
        data={
            "image_based": True,
            "page_images": [
                {"page": 1, "mime_type": "image/png", "base64": "ZmFrZQ=="},
                {"page": 2, "mime_type": "image/png", "base64": "ZmFrZQ=="},
            ],
        },
        metadata={},
    )

    enriched = enrich_image_attachments([parsed])

    assert "Страница 1" in enriched[0].data["image_description"]
    assert len(enriched[0].data["page_descriptions"]) == 2
    assert "[Описание сканированного PDF]" in enriched[0].text


def test_enrich_regular_pdf_adds_visual_summary(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "test-key")
    monkeypatch.setattr(
        "auditmate.tools.images.gemini_vision.describe_image_attachment",
        lambda attachment, model="gemini-2.5-flash-lite", debug_recorder=None, debug_name="": "На странице график и таблица KPI.",
    )

    path = tmp_path / "deck.pdf"
    path.write_bytes(b"fake")
    parsed = ParsedAttachment(
        attachment=create_attachment(path),
        text="[Страница 1]\nRevenue 1000",
        data={
            "image_based": False,
            "image_page_previews": [
                {"page": 1, "mime_type": "image/png", "base64": "ZmFrZQ=="},
                {"page": 2, "mime_type": "image/png", "base64": "ZmFrZQ=="},
            ],
        },
        metadata={},
    )

    enriched = enrich_image_attachments([parsed])

    assert "Страница 1" in enriched[0].data["pdf_visual_summary"]
    assert "[Визуальное описание PDF]" in enriched[0].text
