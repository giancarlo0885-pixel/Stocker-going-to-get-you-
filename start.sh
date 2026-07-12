#!/usr/bin/env bash
set -Eeuo pipefail

echo "Starting GARIBALDI MARKET ORACLE™"

WORKER_PID=""

start_worker() {
  echo "Launching background worker..."
  python -u oracle_worker.py &
  WORKER_PID=$!
  echo "Worker PID: ${WORKER_PID}"
}

shutdown() {
  echo "Stopping application..."
  if [[ -n "${WORKER_PID}" ]] && kill -0 "${WORKER_PID}" 2>/dev/null; then
    kill "${WORKER_PID}" 2>/dev/null || true
    wait "${WORKER_PID}" 2>/dev/null || true
  fi
}
trap shutdown EXIT INT TERM

supervise_worker() {
  while true; do
    if ! kill -0 "${WORKER_PID}" 2>/dev/null; then
      echo "Worker exited. Restarting in 10 seconds..."
      sleep 10
      start_worker
    fi
    sleep 5
  done
}

start_worker
supervise_worker &

exec streamlit run app.py \
  --server.port="${PORT:-8501}" \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --browser.gatherUsageStats=false
