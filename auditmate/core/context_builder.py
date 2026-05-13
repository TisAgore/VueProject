from dataclasses import dataclass, field
from typing import Any

from auditmate.models.attachments import ParsedAttachment


@dataclass
class UnifiedContext:
    """Нормализованный контекст анализа, собранный из питча и вложений."""

    executive_summary: str = ""
    key_metrics: dict[str, Any] = field(default_factory=dict)
    team_info: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    visual_insights: list[str] = field(default_factory=list)
    raw_context: str = ""
    attachments: list[ParsedAttachment] = field(default_factory=list)

    def to_prompt_text(self) -> str:
        """Преобразует единый контекст в текст для LLM-провайдеров."""

        sections = []
        if self.executive_summary:
            sections.append(f"Краткое резюме:\n{self.executive_summary}")
        if self.key_metrics:
            sections.append(f"Ключевые метрики:\n{self.key_metrics}")
        if self.team_info:
            sections.append("Информация о команде:\n" + "\n".join(f"- {item}" for item in self.team_info))
        if self.risks:
            sections.append("Потенциальные риски:\n" + "\n".join(f"- {item}" for item in self.risks))
        if self.visual_insights:
            sections.append("Визуальные наблюдения:\n" + "\n".join(f"- {item}" for item in self.visual_insights))
        if self.raw_context:
            sections.append(f"Исходный контекст:\n{self.raw_context}")

        return "\n\n---\n\n".join(sections).strip()


class ContextBuilder:
    """Собирает единый объект контекста для агентов и синтезатора."""

    METRIC_MARKERS = (
        "revenue",
        "arr",
        "mrr",
        "tam",
        "sam",
        "som",
        "cac",
        "ltv",
        "burn",
        "runway",
        "nps",
        "выруч",
        "рынок",
        "привлекаем",
    )
    TEAM_MARKERS = ("team", "команда", "ceo", "cto", "coo", "founder", "фаундер")
    RISK_MARKERS = ("risk", "рис", "blocker", "угроз", "слаб", "конкур")

    def build(self, pitch_text: str, attachments: list[ParsedAttachment] | None = None) -> UnifiedContext:
        """Объединяет текст питча и распарсенные вложения в UnifiedContext."""

        attachments = attachments or []
        raw_parts = [pitch_text.strip()] if pitch_text.strip() else []

        for parsed in attachments:
            if parsed.text.strip():
                raw_parts.append(f"[Attachment: {parsed.attachment.path.name}]\n{parsed.text.strip()}")

        raw_context = "\n\n".join(raw_parts)
        lines = [line.strip() for line in raw_context.splitlines() if line.strip()]

        return UnifiedContext(
            executive_summary=self._build_executive_summary(lines),
            key_metrics=self._extract_key_metrics(lines, attachments),
            team_info=self._extract_matching_lines(lines, self.TEAM_MARKERS),
            risks=self._extract_matching_lines(lines, self.RISK_MARKERS),
            visual_insights=self._extract_visual_insights(attachments),
            raw_context=raw_context,
            attachments=attachments,
        )

    def _build_executive_summary(self, lines: list[str], max_lines: int = 8) -> str:
        """Создаёт короткое детерминированное резюме из первых содержательных строк."""

        return "\n".join(lines[:max_lines])

    def _extract_key_metrics(self, lines: list[str], attachments: list[ParsedAttachment]) -> dict[str, Any]:
        """Собирает найденные метрики из текста и структурированных вложений."""

        metrics = self._extract_matching_lines(lines, self.METRIC_MARKERS)
        result: dict[str, Any] = {}
        if metrics:
            result["detected_lines"] = metrics

        structured_metrics = {}
        evidence = {}
        for parsed in attachments:
            financial_metrics = parsed.data.get("financial_metrics")
            if financial_metrics:
                structured_metrics[parsed.attachment.path.name] = financial_metrics
            financial_evidence = parsed.data.get("financial_evidence")
            if financial_evidence:
                evidence[parsed.attachment.path.name] = financial_evidence

        if structured_metrics:
            result["financial_metrics"] = structured_metrics
        if evidence:
            result["financial_evidence"] = evidence

        return result

    def _extract_matching_lines(self, lines: list[str], markers: tuple[str, ...]) -> list[str]:
        """Возвращает уникальные строки, содержащие хотя бы один заданный маркер."""

        matches = []
        seen = set()
        for line in lines:
            lower = line.lower()
            if any(marker in lower for marker in markers) and line not in seen:
                matches.append(line)
                seen.add(line)

        return matches

    def _extract_visual_insights(self, attachments: list[ParsedAttachment]) -> list[str]:
        """Собирает описания изображений и других визуальных вложений в отдельный блок."""

        insights = []
        for parsed in attachments:
            description = parsed.data.get("image_description")
            if description:
                insights.append(f"{parsed.attachment.path.name}: {description}")

        return insights
