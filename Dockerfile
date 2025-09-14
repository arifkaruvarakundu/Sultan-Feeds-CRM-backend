# Use official Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app code
COPY . .

# CMD ["uvicorn", "crm_backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
# CMD ["gunicorn", "crm_backend.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]

# Default to development with reload (can be overridden in docker-compose)
CMD ["sh", "-c", "\
    if [ \"$APP_ENV\" = 'prod' ]; then \
      gunicorn crm_backend.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000; \
    else \
      uvicorn crm_backend.main:app --host 0.0.0.0 --port 8000 --reload; \
    fi \
"]