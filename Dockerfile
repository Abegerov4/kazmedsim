FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

# Install deps first for Docker layer caching
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install -r backend/requirements.txt

# Copy backend code, prompts, seeds
COPY backend/ ./backend/
COPY scripts/ ./scripts/

# Schema lives OUTSIDE /app/db — volume mounts overlay /app/db and would hide it.
COPY db/schema.sql /app/schema.sql

# Entrypoint initializes DB on first boot (volume may be empty)
COPY scripts/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

# Persistent SQLite lives here. PaaS volumes mount over this dir.
RUN mkdir -p /app/db
ENV DB_PATH=/app/db/kazmedsim.db \
    SCHEMA_PATH=/app/schema.sql

EXPOSE 8000

CMD ["./entrypoint.sh"]
