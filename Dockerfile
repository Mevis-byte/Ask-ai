# Build stage
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Install the package in editable mode or just install it
RUN pip install --no-cache-dir -e ".[rag]"

# Environment variables
ENV ASK_OLLAMA_HOST=http://host.docker.internal:11434
ENV ASK_MEMORY_PERSIST_PATH=/data/chat.sqlite
ENV ASK_RAG_PERSIST_DIR=/data/rag_index
ENV PYTHONUNBUFFERED=1

# Create data directory
RUN mkdir -p /data

# Default command
ENTRYPOINT ["python", "-m", "ask.main"]
CMD ["ai"]
