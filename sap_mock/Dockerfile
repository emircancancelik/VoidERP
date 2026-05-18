FROM python:3.10-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mock_sap.py .
CMD ["uvicorn", "mock_sap:app", "--host", "0.0.0.0", "--port", "8000"]