from auditmate.core.context_builder import ContextBuilder
from auditmate.models.attachments import ParsedAttachment, create_attachment
from auditmate.tools.parsers import parse_attachment


def test_context_builder_includes_text_and_financial_metrics(tmp_path):
    path = tmp_path / "metrics.csv"
    path.write_text("metric,value\nARR,1200000\nrunway,18\n", encoding="utf-8")
    parsed = parse_attachment(path)

    context = ContextBuilder().build(
        "Команда: CEO Test\nРиск: конкуренты\nRunway: 12 месяцев",
        [parsed],
    )

    assert "Runway: 12 месяцев" in context.key_metrics["detected_lines"]
    assert context.key_metrics["financial_metrics"]["metrics.csv"]["arr"] == "1200000"
    assert context.team_info == ["Команда: CEO Test"]
    assert context.risks == ["Риск: конкуренты"]
    assert "metrics.csv" in context.raw_context


def test_context_builder_collects_visual_insights(tmp_path):
    path = tmp_path / "image.png"
    path.write_bytes(b"fake")
    parsed = ParsedAttachment(
        attachment=create_attachment(path),
        text="[Изображение]",
        data={"image_description": "На графике показан рост ARR до $1.2M."},
        metadata={},
    )

    context = ContextBuilder().build("Pitch text", [parsed])

    assert context.visual_insights == [f"{path.name}: На графике показан рост ARR до $1.2M."]
