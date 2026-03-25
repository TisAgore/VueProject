Проект AuditMate

Этот форк - тестовый. В нем используется FastAPI на backend, также есть только html файл, где указаны функции (как такого фронта на Vue нет). 

Используется huggingface_hub = Inference, где есть бесплатные доступ к моделям (qwen5-72b, chatgpt4-120b, llama и так далее). Все работает, доступ имееется через токен

Нужно создать файл .env
#------------------------------------------------
# Нужно создать токен    Hugging Face Access Token: https://huggingface.co/settings/tokens

HF_TOKEN=your_api_key

# Модель для инференса — любая, доступная через HF Inference API
# Примеры:
#   openai/gpt-oss-120b         (по умолчанию)
#   meta-llama/Llama-3.3-70B-Instruct
#   mistralai/Mistral-7B-Instruct-v0.3
#   Qwen/Qwen2.5-72B-Instruct

HF_MODEL=openai/gpt-oss-120b



# Порт на котором запускается сервер (по умолчанию 8000)

PORT=8000
#------------------------------------------------
