#!/usr/bin/env bash

set -euo pipefail

cleanup_done=0

cleanup() {
  if [[ "$cleanup_done" -eq 1 ]]; then
    return 0
  fi

  cleanup_done=1
  trap '' SIGINT SIGTERM EXIT

  echo ""
  echo "--- Stopping and cleaning up ---"
  docker compose down --remove-orphans >/dev/null 2>&1 || true
  docker image prune -f >/dev/null 2>&1 || true
  echo "Cleanup complete."
}

trap cleanup SIGINT SIGTERM EXIT

echo "Performing initial cleanup..."
docker compose down --remove-orphans >/dev/null 2>&1 || true

echo "Building and starting app..."
docker compose up -d --build

echo "Streaming logs from app. Press Ctrl+C to stop and clean up."
docker compose logs -f app
