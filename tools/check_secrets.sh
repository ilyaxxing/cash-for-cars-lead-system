#!/usr/bin/env bash
#
# Secret and personal data scan.
#
#   tools/check_secrets.sh --staged   # what is about to be committed (pre-commit hook)
#   tools/check_secrets.sh --all      # full git history and every tracked file (before push)
#
# gitleaks looks for credentials, tools/pii_scan.py for real people's data.
# Both must pass: a leaked key can be rotated, a leaked phone number cannot.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

mode="${1:---staged}"

if ! command -v gitleaks >/dev/null 2>&1; then
    echo "gitleaks is not installed: https://github.com/gitleaks/gitleaks#installing" >&2
    exit 1
fi

case "$mode" in
    --staged)
        gitleaks git --pre-commit --staged --redact --no-banner --log-level warn .
        python3 tools/pii_scan.py --staged
        ;;
    --all)
        gitleaks git --redact --no-banner --log-level warn .
        python3 tools/pii_scan.py --tracked
        ;;
    *)
        echo "usage: $0 [--staged | --all]" >&2
        exit 2
        ;;
esac
