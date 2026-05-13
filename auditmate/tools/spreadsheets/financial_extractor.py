from dataclasses import dataclass, field
from typing import Any


METRIC_ALIASES = {
    "revenue": ("revenue", "выручка", "доход"),
    "arr": ("arr", "annual recurring revenue"),
    "mrr": ("mrr", "monthly recurring revenue"),
    "burn_rate": ("burn", "burn rate", "расход", "сжигание"),
    "runway_months": ("runway", "месяц", "months runway"),
    "cac": ("cac", "customer acquisition cost"),
    "ltv": ("ltv", "lifetime value"),
    "growth": ("growth", "рост"),
}


@dataclass
class FinancialExtractionResult:
    """Результат эвристического извлечения финансовых метрик из таблицы."""

    metrics: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, list[str]] = field(default_factory=dict)


def extract_financial_metrics(rows: list[dict[str, Any]]) -> FinancialExtractionResult:
    """Извлекает вероятные финансовые метрики из строк таблицы."""

    metrics: dict[str, Any] = {}
    evidence: dict[str, list[str]] = {}

    for row in rows:
        searchable = _row_to_searchable_text(row)
        for metric_name, aliases in METRIC_ALIASES.items():
            if any(alias in searchable for alias in aliases):
                evidence.setdefault(metric_name, []).append(searchable)
                value = _first_non_empty_value(row)
                if value is not None and metric_name not in metrics:
                    metrics[metric_name] = value

    return FinancialExtractionResult(metrics=metrics, evidence=evidence)


def _row_to_searchable_text(row: dict[str, Any]) -> str:
    """Преобразует строку таблицы в нижний регистр для поиска маркеров."""

    parts = []
    for key, value in row.items():
        if value is None:
            continue
        parts.append(f"{key}: {value}")

    return " | ".join(parts).lower()


def _first_non_empty_value(row: dict[str, Any]) -> Any:
    """Возвращает первое непустое значение из строки после текстового названия метрики."""

    values = [value for value in row.values() if value not in (None, "")]
    if len(values) >= 2:
        return values[1]
    if values:
        return values[0]

    return None
