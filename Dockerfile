# Используем официальный образ Python
FROM python:3.12-slim

# Устанавливаем зависимости для Chrome
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    chromium \
    chromium-driver \
    cron \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Установка временной зоны (например, Europe/Moscow)
ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Создаем рабочую директорию
WORKDIR /app

# Устанавливаем Python-библиотеки
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY src/ ./src/
COPY scripts/ ./scripts/

# Даем скриптам права на выполнение
RUN chmod +x ./scripts/*.sh

# Настройки для Chrome в headless-режиме
ENV SE_OPTS="--headless --no-sandbox --disable-dev-shm-usage"

# Запуск
CMD ["python", "src/main.py"]
