#!/usr/bin/env bash
set -euo pipefail

# Quick test runner for ingredient endpoints
# Usage:
#   ./scripts/test_ingredients_endpoints.sh
#   BASE_URL=http://localhost:8003/api/v1 ./scripts/test_ingredients_endpoints.sh

BASE_URL=${BASE_URL:-http://localhost:8000/api/v1}

echo "Testing against: ${BASE_URL}"

function hit() {
  local path="$1"
  local label="$2"
  echo
  echo "==> ${label}: ${path}"
  http_code=$(curl -sS -w "%{http_code}" -o /tmp/resp.json "${BASE_URL}${path}" || true)
  echo "Status: ${http_code}"
  if [[ -s /tmp/resp.json ]]; then
    echo "Body (truncated):"
    head -c 600 /tmp/resp.json; echo
  else
    echo "No body returned"
  fi
}

hit "/ingredients/MSG/analysis" "Ingredient analysis (MSG)"
hit "/ingredients/E250/analysis" "Ingredient analysis (E250)"
hit "/ingredients/health" "Ingredients health check"

echo
echo "Done."

