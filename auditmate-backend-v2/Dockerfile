FROM python:3.11-slim

WORKDIR /app

# Зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Исходный код
COPY . .

# Запуск
CMD ["python", "run.py"]
