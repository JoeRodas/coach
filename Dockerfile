FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends stockfish \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install CPU-only torch first so sentence-transformers doesn't pull the full
# CUDA stack (~2 GB of drivers we can't use on Fly's shared-CPU VMs).
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir -e ".[web]"

COPY data/index.npz ./data/index.npz

ENV STOCKFISH_PATH=/usr/games/stockfish
ENV STOCKFISH_DEPTH=12
ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "coach.web:app", "--host", "0.0.0.0", "--port", "8080"]
