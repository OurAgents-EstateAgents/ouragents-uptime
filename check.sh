#!/usr/bin/env bash
# Checks each URL loads (HTTP 200). A URL that fails is retried once after
# RETRY_WAIT seconds so a single blip does not send an alert.
# Exit 0 = all up, 1 = at least one down.
set -u
RETRY_WAIT=${RETRY_WAIT:-60}
UA="OurAgentsUptimeCheck/1.0 (+https://github.com/OurAgents-EstateAgents/ouragents-uptime)"
status() { curl -s -o /dev/null -w '%{http_code}' --max-time 30 -A "$UA" "$1"; }
down=0
for url in "$@"; do
  code=$(status "$url")
  if [ "$code" != "200" ]; then
    sleep "$RETRY_WAIT"
    code=$(status "$url")
  fi
  if [ "$code" = "200" ]; then
    echo "UP   $code $url"
  else
    echo "DOWN $code $url"
    down=1
  fi
done
exit $down
