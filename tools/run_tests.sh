#!/usr/bin/env bash
#
# Run the Python test suite against a throwaway PostgreSQL.
#
#   tools/run_tests.sh              # all tests
#   tools/run_tests.sh -k preset    # extra arguments go to pytest
#
# Uses TEST_DATABASE_URL when it is set. Otherwise starts a temporary cluster
# with the local PostgreSQL binaries (initdb/pg_ctl), or a Docker container if
# those are not installed. The database is created empty, migrated by the
# tests themselves and removed afterwards: the development database is never
# touched.

set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-.venv/bin/python}"
PORT="${TEST_PG_PORT:-55432}"
DB_NAME="carbuyout_test"

# On macOS the postmaster refuses to start without a C locale. Only the
# PostgreSQL tools get it: Python needs UTF-8.
pg() { LC_ALL=C LANG=C "$@"; }

if [[ -n "${TEST_DATABASE_URL:-}" ]]; then
    echo "using TEST_DATABASE_URL"
elif command -v pg_ctl >/dev/null 2>&1 && command -v initdb >/dev/null 2>&1; then
    PGDATA="$(mktemp -d "${TMPDIR:-/tmp}/carbuyout-tests.XXXXXX")"
    cleanup() {
        pg pg_ctl -D "$PGDATA" -m immediate -w stop >/dev/null 2>&1 || true
        rm -rf "$PGDATA"
    }
    trap cleanup EXIT
    echo "starting a temporary PostgreSQL on port $PORT"
    pg initdb -D "$PGDATA" -U postgres --auth=trust >/dev/null
    pg pg_ctl -D "$PGDATA" \
        -o "-p $PORT -c listen_addresses=127.0.0.1 -c unix_socket_directories=''" \
        -l "$PGDATA/postgres.log" -w start >/dev/null
    pg createdb -h 127.0.0.1 -p "$PORT" -U postgres "$DB_NAME"
    export TEST_DATABASE_URL="postgresql+asyncpg://postgres@127.0.0.1:$PORT/$DB_NAME"
elif command -v docker >/dev/null 2>&1; then
    CONTAINER="carbuyout-tests-$$"
    trap 'docker rm -f "$CONTAINER" >/dev/null 2>&1 || true' EXIT
    echo "starting a temporary PostgreSQL container on port $PORT"
    docker run -d --rm --name "$CONTAINER" \
        -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB="$DB_NAME" \
        -p "127.0.0.1:$PORT:5432" postgres:18-alpine >/dev/null
    for _ in $(seq 1 30); do
        docker exec "$CONTAINER" pg_isready -U postgres -d "$DB_NAME" >/dev/null 2>&1 && break
        sleep 1
    done
    export TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@127.0.0.1:$PORT/$DB_NAME"
else
    echo "Need PostgreSQL binaries, Docker, or TEST_DATABASE_URL to run the tests." >&2
    exit 1
fi

"$PYTHON" -m pytest "$@"
