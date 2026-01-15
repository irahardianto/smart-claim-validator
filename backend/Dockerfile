FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for SQLite
RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*

# Copy backend code
COPY backend/ /app/backend/

# Install dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=True

# Expose port (Cloud Run sets PORT env var, defaults to 8080)
ENV PORT=8080

# Command to run the application using generic python (POC) or gunicorn could be used.
# For this POC, we reuse server.py, but ensure it listens on PORT.
CMD ["python", "backend/server.py"]
