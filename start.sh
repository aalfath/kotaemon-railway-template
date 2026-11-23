#!/bin/sh
# Railway entrypoint for Kotaemon. Any crash exits non-zero so Railway's ON_FAILURE policy restarts it.
set -e
export GRADIO_SERVER_NAME="${GRADIO_SERVER_NAME:-0.0.0.0}"
export GRADIO_SERVER_PORT="${PORT:-7860}"
# Configured from Railway variables, so skip upstream's first-run provider wizard.
export KH_ENABLE_FIRST_SETUP="${KH_ENABLE_FIRST_SETUP:-false}"
# Graph RAG back-ends are not installed in this image (size and memory).
export USE_MS_GRAPHRAG="${USE_MS_GRAPHRAG:-false}" USE_LIGHTRAG="${USE_LIGHTRAG:-false}" USE_NANO_GRAPHRAG="${USE_NANO_GRAPHRAG:-false}"
# Small Railway plans: keep numeric libraries to the service's CPUs, not the host's.
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}" OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}" \
       MKL_NUM_THREADS="${MKL_NUM_THREADS:-2}" NUMEXPR_MAX_THREADS="${NUMEXPR_MAX_THREADS:-2}" \
       TOKENIZERS_PARALLELISM=false
if [ -z "${KH_FEATURE_USER_MANAGEMENT_PASSWORD:-}" ] || [ "$KH_FEATURE_USER_MANAGEMENT_PASSWORD" = "admin" ]; then
  echo "KH_FEATURE_USER_MANAGEMENT_PASSWORD must be set to a strong password (not 'admin')." >&2
  exit 1
fi
mkdir -p /app/ktem_app_data
cd /app
exec /app/.venv/bin/python /app/railway_app.py
