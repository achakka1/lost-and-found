FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run only allows writing to /tmp
ENV DB_PATH=/tmp/lostfound.db

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app