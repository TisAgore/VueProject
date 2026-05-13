from auditmate.models.responses import OptimistResponse
from auditmate.utils.json import parse_llm_json, strip_json


def test_strip_json_removes_markdown_fence():
    raw = """```json
{"value": 1}
```"""

    assert strip_json(raw) == '{"value": 1}'


def test_parse_llm_json_validates_schema():
    raw = """
    {
      "strengths": [{"point": "traction", "detail": "NPS 71", "impact": "high"}],
      "hidden_gems": ["offline model"],
      "best_case_scenario": "Рост в нескольких регионах.",
      "score": 8,
      "score_rationale": "Сильная команда и traction."
    }
    """

    parsed = parse_llm_json(raw, OptimistResponse)

    assert parsed.score == 8
    assert parsed.strengths[0].impact == "high"


def test_parse_llm_json_repairs_minor_malformed_json():
    raw = """
    {
      "strengths": [{"point": "traction", "detail": "NPS 71", "impact": "high"}],
      "hidden_gems": ["offline model"],
      "best_case_scenario": "Рост",
      "score": 8,
      "score_rationale": "Сильная команда",
    }
    """

    parsed = parse_llm_json(raw, OptimistResponse)

    assert parsed.score == 8

