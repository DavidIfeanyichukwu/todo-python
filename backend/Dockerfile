# Backend Service - Python Flask REST API
# python:3.12-slim keeps the image lightweight (~150 MB vs ~1 GB for full python)
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so this layer is cached between builds
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then copy the application code
COPY app.py .

# Run as a non-root user (container security best practice)
RUN useradd --create-home appuser
USER appuser

EXPOSE 5000

# gunicorn is a production WSGI server (Flask's dev server is not)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
