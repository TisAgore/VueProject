import argparse
import json
from dataclasses import asdict

from auditmate.core.evaluator import evaluate_pitch
from auditmate.core.reporting import print_report
from auditmate.providers.catalog import DEFAULT_MODEL_KEY, LMSTUDIO_BASE_URL, print_available_models


SAMPLE_PITCH = """
Стартап: AgroSense AI

Проблема: 40% урожая в развивающихся странах теряется из-за несвоевременного
обнаружения болезней растений. Фермеры узнают о проблеме слишком поздно.

Решение: Мобильное приложение на основе computer vision. Фермер фотографирует
листья растений — AI за 3 секунды определяет болезнь и даёт рекомендации
по лечению. Работает офлайн (модель на устройстве).

Рынок: TAM $85 млрд (мировой рынок агрострахования + средства защиты растений).
Целевой сегмент — Индия, Бразилия, Нигерия. SAM $12 млрд.

Бизнес-модель: Freemium. Базовая диагностика бесплатно, расширенные функции
(история болезней, рекомендации удобрений, агроном онлайн) — $3/месяц.
B2B: лицензии для агростраховых компаний — $50k+/год.

Тракция: 45,000 активных пользователей в Индии (6 месяцев после запуска),
NPS 71, 3 пилота с крупными страховыми компаниями.

Команда:
- CEO: Priya Sharma, ex-Google AI, PhD Computer Vision, IIT Delhi
- CTO: Marcus Oliveira, 8 лет в AgriTech, ex-Bayer Digital Farming
- COO: Amara Osei, ex-Olam International, 10 лет операций в Африке

Привлекаем: $3M Seed. Использование: 60% product, 25% GTM Индия+Нигерия, 15% ops.
Runway: 24 месяца. Целевой ARR через 24м: $2.4M.
"""


def main() -> None:
    """Разбирает аргументы CLI, запускает AuditMate и сохраняет отчёт комитета."""

    parser = argparse.ArgumentParser(
        description="AuditMate оценка стартапов (OpenRouter + LM Studio)",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_KEY,
        help=(
            "Модель для всех агентов.\n"
            "Облако: auto\n"
            "Локально: local | qwen2.5-3b | qwen2.5-7b | llama3.2-3b | phi3.5-mini | gemma3-4b\n"
            f"По умолчанию: {DEFAULT_MODEL_KEY}"
        ),
    )
    parser.add_argument(
        "--synthesizer-model",
        default=None,
        help="Модель синтезатора (если отличается от --model). Пример: --model local --synthesizer-model auto",
    )
    parser.add_argument(
        "--lmstudio-url",
        default=LMSTUDIO_BASE_URL,
        help=f"URL сервера LM Studio (по умолчанию: {LMSTUDIO_BASE_URL})",
    )
    parser.add_argument(
        "--pitch-file",
        default=None,
        help="Путь к .txt файлу с питчем (без флага используется встроенный пример)",
    )
    parser.add_argument(
        "--attachment",
        action="append",
        default=[],
        help=(
            "Дополнительный файл контекста: .txt, .md, .json, .csv, .xlsx или .xls. "
            "Также поддерживаются .pdf, .docx и изображения. "
            "Изображения и сканированные PDF при наличии GOOGLE_AI_API_KEY будут автоматически описаны через Gemini. "
            "Флаг можно повторять несколько раз."
        ),
    )
    parser.add_argument(
        "--output",
        default="committee_report.json",
        help="Путь для сохранения JSON-отчёта",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        default=None,
        help="Запускать агентов последовательно, по одному.",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        default=False,
        help="Принудительно параллельный запуск даже для локальных моделей.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Пауза в секундах между агентами в sequential-режиме.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        dest="max_retries",
        help="Максимум повторов при ошибке 429 Rate Limit.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Сохранять context, prompts, raw responses и repaired JSON в debug-директорию.",
    )
    parser.add_argument(
        "--debug-dir",
        default=".auditmate_debug",
        help="Директория для debug-артефактов.",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Показать список доступных моделей и выйти",
    )

    args = parser.parse_args()

    if args.list_models:
        print_available_models()
        raise SystemExit(0)

    if args.sequential:
        sequential = True
    elif args.parallel:
        sequential = False
    else:
        sequential = None

    pitch = SAMPLE_PITCH
    if args.pitch_file:
        with open(args.pitch_file, encoding="utf-8") as f:
            pitch = f.read()

    report = evaluate_pitch(
        pitch_text=pitch,
        attachment_paths=args.attachment,
        model_key=args.model,
        synthesizer_model=args.synthesizer_model,
        lmstudio_url=args.lmstudio_url,
        sequential=sequential,
        delay=args.delay,
        max_retries=args.max_retries,
        debug=args.debug,
        debug_dir=args.debug_dir,
    )

    print_report(report)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(asdict(report), f, ensure_ascii=False, indent=2)

    print(f"\nОтчёт сохранён: {args.output}")


if __name__ == "__main__":
    main()
