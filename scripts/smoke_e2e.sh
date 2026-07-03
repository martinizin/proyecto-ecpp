#!/usr/bin/env sh
# Post-deploy smoke test — runs against the public URL after a deploy.
# Usage: BASE_URL=https://ecppp.edu.ec ./scripts/smoke_e2e.sh
# Add -k behaviour for local self-signed certs with INSECURE=1.
set -eu

BASE_URL="${BASE_URL:-https://localhost}"
CURL="curl -sS"
[ "${INSECURE:-0}" = "1" ] && CURL="$CURL -k"

fail() {
    echo "SMOKE FAIL: $1" >&2
    exit 1
}

check_status() {
    _url="$1"
    _expected="$2"
    _code="$($CURL -o /dev/null -w '%{http_code}' "$_url")"
    if [ "$_code" != "$_expected" ]; then
        fail "$_url returned $_code, expected $_expected"
    fi
    echo "OK  $_url -> $_code"
}

echo "Smoke test against $BASE_URL"

# 1. Health endpoint is up and reports healthy.
health="$($CURL "$BASE_URL/health/")"
echo "$health" | grep -q '"status": "ok"' || fail "/health/ not ok: $health"
echo "OK  /health/ -> $health"

# 2. Login page renders (exercises WhiteNoise static manifest).
check_status "$BASE_URL/usuarios/login/" 200

# 3. Root redirects to login.
check_status "$BASE_URL/" 302

# 4. A protected page redirects unauthenticated users to login (auth gate works).
check_status "$BASE_URL/usuarios/dashboard/" 302

echo "SMOKE PASS"
