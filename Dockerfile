from python:3.13-slim
ENV PYTHONBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "journey.wsgi", "--bind", "0.0.0.0:8000", "--workers", "2"]
