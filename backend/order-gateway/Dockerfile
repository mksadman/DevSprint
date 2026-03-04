FROM python:3.11-slim

WORKDIR /app

# Install dependencies first — maximises Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

EXPOSE 8000

# The FastAPI app lives in app/main.py → module path is app.main:app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
