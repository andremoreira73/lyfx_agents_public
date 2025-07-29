FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js and npm for Tailwind
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Install Tailwind dependencies
WORKDIR /app/theme/static_src
RUN npm install
WORKDIR /app

# Build Tailwind CSS
RUN cd theme/static_src && npm run build

# Create necessary directories
RUN mkdir -p logs media static staticfiles

# Run Django setup commands
RUN python manage.py collectstatic --noinput || true

# Create a non-root user
ARG UID=1000
ARG GID=1000

RUN groupadd -g $GID appuser && \
    useradd -u $UID -g $GID -m appuser

# Create directory for SQLite checkpoints (will be replaced by PostgreSQL)
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

# Change ownership of the app directory
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Default command (will be overridden by docker-compose)
CMD ["uvicorn", "lyfx_agents.asgi:application", "--host", "0.0.0.0", "--port", "8000"]