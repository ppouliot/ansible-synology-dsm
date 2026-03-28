#!/usr/bin/env bash
# DSM 7 Action Plugin Integration Test Runner
# Runs inside ghcr.io/ansible/community-ansible-dev-tools:latest
# Records output as asciinema cast to assets/test-run.cast

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${REPO_ROOT}/tests/integration/logs"
ASSETS_DIR="${REPO_ROOT}/assets"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="${LOG_DIR}/run-${TIMESTAMP}.log"

mkdir -p "${LOG_DIR}" "${ASSETS_DIR}"

echo "=== DSM 7 Action Plugin Integration Tests ==="
echo "Target:     http://172.19.0.43:5000"
echo "Timestamp:  ${TIMESTAMP}"
echo "Log:        ${LOG_FILE}"
echo "Cast:       ${ASSETS_DIR}/test-run.cast"
echo ""

# Pull latest image
docker pull ghcr.io/ansible/community-ansible-dev-tools:latest

# Run tests inside container, recording with asciinema
docker run --rm \
  -v "${REPO_ROOT}:/workspace" \
  -w /workspace \
  -e ANSIBLE_FORCE_COLOR=1 \
  ghcr.io/ansible/community-ansible-dev-tools:latest \
  bash -c "
    pip install asciinema -q 2>/dev/null || true
    asciinema rec /workspace/assets/test-run.cast \
      --command 'ansible-playbook -i tests/integration/inventory.ini tests/integration/test_dsm7_plugin.yml -v 2>&1 | tee /workspace/${LOG_FILE##${REPO_ROOT}/}' \
      --title 'DSM7 action plugin integration tests - ${TIMESTAMP}' \
      --quiet
  " 2>&1 | tee "${LOG_FILE}"

echo ""
echo "=== Done ==="
echo "Cast file: ${ASSETS_DIR}/test-run.cast"
echo "Log file:  ${LOG_FILE}"
echo ""
echo "To replay: asciinema play ${ASSETS_DIR}/test-run.cast"
