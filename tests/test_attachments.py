from auditmate.models.attachments import create_attachment, detect_attachment_kind


def test_detect_attachment_kind_supported_extensions():
    assert detect_attachment_kind("pitch.txt") == "text"
    assert detect_attachment_kind("notes.md") == "markdown"
    assert detect_attachment_kind("data.json") == "json"
    assert detect_attachment_kind("metrics.csv") == "csv"
    assert detect_attachment_kind("model.xlsx") == "xlsx"
    assert detect_attachment_kind("deck.pdf") == "pdf"
    assert detect_attachment_kind("memo.docx") == "docx"
    assert detect_attachment_kind("chart.png") == "image"


def test_create_attachment_normalizes_kind(tmp_path):
    path = tmp_path / "metrics.csv"
    path.write_text("metric,value\nARR,100\n", encoding="utf-8")

    attachment = create_attachment(path)

    assert attachment.kind == "csv"
    assert attachment.path.name == "metrics.csv"

