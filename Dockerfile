# Kotaemon v0.12.0 for Railway, built from the pinned upstream release tag.
# Upstream's own v0.12.0 image (ghcr.io/cinnamon/kotaemon:main-lite) is ~4.9 GB compressed
# because it pulls CUDA torch; Railway's Free/Trial plans cap images at 4 GB. This build
# installs upstream's locked dependency versions (uv.lock) minus the GPU / local-model extras.
ARG KOTAEMON_VERSION=v0.12.0
ARG KOTAEMON_COMMIT=9ad3e4e49aa35b8acddd235918a5d9753c1cfdf9

FROM python:3.11.14-slim-trixie@sha256:c8271b1f627d0068857dce5b53e14a9558603b527e46f1f901722f935b786a39 AS build
ARG KOTAEMON_VERSION
ARG KOTAEMON_COMMIT
ENV PYTHONDONTWRITEBYTECODE=1 UV_LINK_MODE=copy UV_NO_CACHE=1
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends git curl unzip gcc g++ ca-certificates >/dev/null \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -q uv==0.9.5
RUN git clone -q --depth 1 --branch "$KOTAEMON_VERSION" https://github.com/Cinnamon/kotaemon /app \
 && test "$(git -C /app rev-parse HEAD)" = "$KOTAEMON_COMMIT"
WORKDIR /app
COPY excluded-packages.txt /tmp/excluded-packages.txt
# Locked versions from upstream's uv.lock, without CUDA torch, local-model and OCR extras.
RUN uv export --frozen --no-dev --no-hashes --no-emit-workspace --no-header --no-annotate -o /tmp/req-all.txt \
 && grep -v -E -i -f /tmp/excluded-packages.txt /tmp/req-all.txt > /tmp/req.txt \
 && uv venv -q --python /usr/local/bin/python3 /app/.venv \
 && uv pip install -q --python /app/.venv --no-deps -r /tmp/req.txt \
 && uv pip install -q --python /app/.venv --no-deps -e libs/kotaemon -e libs/ktem \
 && rm -r /app/.git /app/docs /app/.github
# PDF.js viewer, tiktoken encodings and NLTK data, so the first boot needs no downloads.
ENV TIKTOKEN_CACHE_DIR=/app/.cache/tiktoken
RUN bash scripts/download_pdfjs.sh /app/libs/ktem/ktem/assets/prebuilt/pdfjs-dist >/dev/null \
 && /app/.venv/bin/python -c "import tiktoken; tiktoken.encoding_for_model('gpt-3.5-turbo'); tiktoken.get_encoding('cl100k_base')" \
 && /app/.venv/bin/python -c "from llama_index.core.readers.base import BaseReader" \
 && find /app/.venv -name '__pycache__' -prune -exec rm -r {} + \
 && : > /app/.env

FROM python:3.11.14-slim-trixie@sha256:c8271b1f627d0068857dce5b53e14a9558603b527e46f1f901722f935b786a39
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends poppler-utils libmagic1 ca-certificates >/dev/null \
 && rm -rf /var/lib/apt/lists/*
COPY --from=build /app /app
COPY railway_app.py lazy_umap.py start.sh /app/
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONIOENCODING=UTF-8 TIKTOKEN_CACHE_DIR=/app/.cache/tiktoken \
    KH_APP_VERSION=0.12.0 MALLOC_ARENA_MAX=2 GRADIO_ANALYTICS_ENABLED=False HF_HUB_DISABLE_TELEMETRY=1 ANONYMIZED_TELEMETRY=False
EXPOSE 7860
CMD ["sh", "/app/start.sh"]
