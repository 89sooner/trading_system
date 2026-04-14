FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
# Copy uv.lock only if present (optional lockfile).
COPY uv.lock* ./
COPY src/ ./src/
COPY configs/ ./configs/

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn trading_system.api.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
