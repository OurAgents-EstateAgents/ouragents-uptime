#!/usr/bin/env bash
# Tests check.sh against a local server: 200 passes, 404 and no-server fail.
set -u
cd "$(dirname "$0")/.."
ROOT=$(mktemp -d); echo ok > "$ROOT/up.html"
python3 -m http.server 8765 --directory "$ROOT" >/dev/null 2>&1 & SRV=$!
trap 'kill $SRV' EXIT; sleep 1
fail=0
expect() { # expect <exit-code> <urls...>
  local want=$1; shift
  RETRY_WAIT=0 ./check.sh "$@" >/dev/null 2>&1; local got=$?
  if [ "$got" = "$want" ]; then echo "PASS $*"; else echo "FAIL $* (exit $got, want $want)"; fail=1; fi
}
expect 0 http://127.0.0.1:8765/up.html
expect 1 http://127.0.0.1:8765/missing.html
expect 1 http://127.0.0.1:8765/up.html http://127.0.0.1:8765/missing.html
expect 1 http://127.0.0.1:9/nothing-listening
exit $fail
