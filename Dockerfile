FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port
EXPOSE 8000

# Set environment variables for development
ENV ENABLE_AUTH_BYPASS=true
ENV DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:54322/postgres
ENV SECRET_KEY=super-secret-jwt-token-with-at-least-32-characters-long

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 