#!/usr/bin/env bash
#
# Everything that must pass before a push.
#
#   tools/check.sh
#
# Lint, tests on a throwaway database, frontend type check and build, and a
# full secret and personal data scan of the history.

set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-.venv/bin/python}"

echo "== python lint"
"$PYTHON" -m ruff check app tests tools
"$PYTHON" -m ruff format --check app tests tools

echo "== python tests"
tools/run_tests.sh -q

echo "== frontend"
npm --prefix frontend run --silent check
npm --prefix frontend run --silent test
npm --prefix frontend run --silent build >/dev/null

echo "== secrets and personal data"
tools/check_secrets.sh --all

echo "all checks passed"
