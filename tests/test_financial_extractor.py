from auditmate.tools.spreadsheets.financial_extractor import extract_financial_metrics


def test_extract_financial_metrics_from_rows():
    result = extract_financial_metrics(
        [
            {"metric": "ARR", "value": 1200000},
            {"metric": "burn rate", "value": 50000},
            {"metric": "runway", "value": 18},
        ]
    )

    assert result.metrics["arr"] == 1200000
    assert result.metrics["burn_rate"] == 50000
    assert result.metrics["runway_months"] == 18
    assert "arr" in result.evidence

