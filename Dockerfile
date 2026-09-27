FROM python:3.12-slim

# Системные пакеты, нужные для сборки cryptography/cffi (jwcrypto, python-keycloak)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Сначала зависимости — для использования кеша слоёв Docker
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Копируем только то, что нужно приложению в рантайме
COPY app ./app
COPY main.py .

# Директории для рантайм-данных (файлы, аудит).
# В compose они будут перекрыты volume-ами — но нужны и для одиночного `docker run`.
RUN mkdir -p upload_files download_files uploads

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
