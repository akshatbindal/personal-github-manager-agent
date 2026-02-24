FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure the src directory is in PYTHONPATH
ENV PYTHONPATH=/app

CMD ["./start.sh"]
