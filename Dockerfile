FROM python:3.11-slim

LABEL maintainer="instock"
LABEL description="InStock FastAPI - Stock Analysis System"

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    build-essential \
    libtool \
    autoconf \
    automake \
    && rm -rf /var/lib/apt/lists/*

RUN wget -q https://sourceforge.net/projects/ta-lib/files/ta-lib/0.4.0/ta-lib-0.4.0-src.tar.gz/download -O ta-lib.tar.gz \
    && tar -xzf ta-lib.tar.gz \
    && cd ta-lib \
    && ./configure --build=x86_64-linux \
    && make \
    && make install \
    && cd .. \
    && rm -rf ta-lib ta-lib.tar.gz \
    && ldconfig

RUN pip install uv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

COPY --chmod=755 ./scripts/start.sh /usr/local/bin/start.sh

COPY . .

RUN mkdir -p /app/logs

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["sh", "-c", "uv run --no-dev uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT:-8000} --workers ${UVICORN_WORKERS:-1}"]
