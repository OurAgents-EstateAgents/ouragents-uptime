#!/usr/bin/env python3
"""Alert when ouragents.co.uk stops loading.

The pages are loaded every 5 minutes by a scheduled job in Supabase (the
website host's firewall blocks GitHub's servers, but not Supabase's). This
script reads those results and exits 1 - which makes GitHub email the
owner - when a page failed twice in a row, when results are missing, or
when the latest results are more than 15 minutes old.
"""
import json, os, sys, urllib.request
from datetime import datetime, timedelta, timezone

SUPABASE_URL = "https://niokqzlfxpelgqqujeuy.supabase.co"
PAGES = 3
STALE = timedelta(minutes=15)


def is_up(status):
    return status == 200


def problems(rows, now):
    found = []
    if len(rows) < PAGES:
        found.append(f"only {len(rows)} of {PAGES} pages have results - the Supabase check may have stopped")
    for r in rows:
        checked = datetime.fromisoformat(r["last_checked"])
        if now - checked > STALE:
            found.append(f"{r['url']}: last checked {checked:%H:%M} UTC - the Supabase check may have stopped")
        elif not is_up(r["last_status"]) and not is_up(r["prev_status"]):
            found.append(f"{r['url']}: DOWN twice running "
                         f"({r['last_status'] or r['last_error']}, then {r['prev_status'] or r['prev_error']})")
    return found


def fetch(key):
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/rpc/uptime_status", data=b"{}", method="POST",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main():
    if os.environ.get("FORCE_ALERT") == "true":
        print("TEST ALERT: this run was started by hand to check that the alert email arrives.")
        return 1
    rows = fetch(os.environ["SUPABASE_KEY"])
    for r in rows:
        print(f"{'UP  ' if is_up(r['last_status']) else 'DOWN'} {r['last_status'] or r['last_error']} "
              f"{r['url']} (checked {r['last_checked'][11:16]} UTC)")
    found = problems(rows, datetime.now(timezone.utc))
    for p in found:
        print("ALERT:", p)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
