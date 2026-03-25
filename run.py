"""
Точка входа: python run.py
Загружает .env и запускает uvicorn.
"""
import os
from pathlib import Path

# Загружаем .env если он существует
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
    print("✅ .env загружен")
except ImportError:
    pass  # python-dotenv не установлен — используем системные переменные

import uvicorn

if __name__ == "__main__":
    port     = int(os.getenv("PORT", 8000))
    hf_token = os.getenv("HF_TOKEN", "")
    hf_model = os.getenv("HF_MODEL", "openai/gpt-oss-120b")

    if not hf_token:
        print("⚠️  ВНИМАНИЕ: HF_TOKEN не задан!")
        print("   Создайте файл .env (см. .env.example) или задайте переменную окружения.")
    else:
        print(f"🔑 HF Token загружен (hf_...{hf_token[-6:]})")

    print(f"🤖 Модель: {hf_model}")
    print(f"🚀 Запуск AuditMate API на http://localhost:{port}")
    print(f"📖 Документация: http://localhost:{port}/docs")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
    )
