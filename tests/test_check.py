"""Tests for check.py's alert rule (no network)."""
import sys, os
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from check import problems

now = datetime(2026, 10, 21, 15, 0, tzinfo=timezone.utc)
fresh = (now - timedelta(minutes=3)).isoformat()
old = (now - timedelta(minutes=30)).isoformat()

def row(last, prev, checked=fresh, url="https://www.ouragents.co.uk/"):
    return {"url": url, "last_status": last, "last_error": None, "last_checked": checked,
            "prev_status": prev, "prev_error": None}

three_up = [row(200, 200, url=f"https://x/{i}") for i in range(3)]
cases = [
    ("all up", three_up, 0),
    ("one blip", [row(503, 200)] + three_up[1:], 0),
    ("down twice", [row(403, 403)] + three_up[1:], 1),
    ("no answer twice", [row(None, None)] + three_up[1:], 1),
    ("results stale", [row(200, 200, checked=old)] + three_up[1:], 1),
    ("missing pages", three_up[:1], 1),
    ("nothing at all", [], 1),
]
bad = 0
for name, rows, want in cases:
    got = len(problems(rows, now))
    ok = (got > 0) == (want > 0)
    print("PASS" if ok else "FAIL", name, got)
    bad += not ok

from check import email_kind
# (previous run failed?, this run failed?, minute past the hour) -> email to send
for prev, now_bad, minute, want in [
    (False, True, 17, "down"),       # just went down: tell the owner
    (True, True, 17, None),          # still down: no repeat every 5 minutes
    (True, True, 2, "down"),         # still down: hourly reminder
    (True, False, 17, "up"),         # back up: say so
    (False, False, 17, None),        # all fine: silence
]:
    got = email_kind(prev, now_bad, minute)
    print("PASS" if got == want else "FAIL", "email", prev, now_bad, minute, got)
    bad += got != want
sys.exit(1 if bad else 0)
