# Используем официальный образ Python
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /bot_service

# Копируем файл зависимостей и устанавливаем зависимости
COPY requirements.txt .
#RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код бота в контейнер
COPY . .

# Команда для запуска бота
CMD ["python3", "app.py"]
