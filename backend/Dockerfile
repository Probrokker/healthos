FROM python:3.12-slim

WORKDIR /app

# Системные зависимости для psycopg2 и pdfplumber
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаём папку для загрузок
RUN mkdir -p /app/uploads

EXPOSE 8000

CMD ["python", "main.py"]
