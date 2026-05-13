from auditmate.models.reports import CommitteeReport


def print_report(report: CommitteeReport) -> None:
    """Печатает компактную человекочитаемую версию отчёта комитета."""

    print("ОТЧЁТ ИНВЕСТИЦИОННОГО КОМИТЕТА")

    for ar in report.agent_results:
        print(f"{ar.emoji}  {ar.agent_name.upper()}  · {ar.model_used}  [{ar.provider}]")

        if ar.error:
            print(f"  {ar.error}")
        elif ar.parsed:
            score = ar.parsed.get("score", "N/A")
            rationale = ar.parsed.get("score_rationale", "")
            print(f"  Оценка: {score}/10 - {rationale}")

    if report.synthesis:
        s = report.synthesis
        rec = s.get("investment_recommendation", "unknown")
        labels = {
            "invest": "МОЖНО ИНВЕСТИРОВАТЬ",
            "pass": "НЕЛЬЗЯ ИНВЕСТИРОВАТЬ",
            "more_diligence": "НЕОБХОДИМА ДОРАБОТКА",
        }

        print("РЕШЕНИЕ КОМИТЕТА")
        print(f"\n  Рекомендация:      {labels.get(rec, rec)}")
        print(f"  Взвешенная оценка: {s.get('weighted_score', 'N/A')}/10")
        print(f"\n  Резюме:\n  {s.get('executive_summary', '')}")
        print(f"\n  Обоснование:\n  {s.get('recommendation_rationale', '')}")

        if s.get("critical_blockers"):
            print(f"\n  Блокеры: {', '.join(s['critical_blockers'])}")

        if s.get("next_steps"):
            print("\n  Следующие шаги:")
            for step in s["next_steps"]:
                print(f"    -> {step}")
