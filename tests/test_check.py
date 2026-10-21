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
sys.exit(1 if bad else 0)
