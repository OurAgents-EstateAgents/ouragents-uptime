"""Tests for check.py's decision rule (no network)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from check import verdict

ok = [[1, 0.2, "OK", "200", "1.1.1.1"]]
forbidden = [[1, 0.2, "Forbidden", "403", "1.1.1.1"]]
timeout = [[0, 30, "Connection timed out", None, None]]

cases = [
    ({"a": ok, "b": ok, "c": ok}, "up"),
    ({"a": ok, "b": forbidden, "c": ok}, "up"),            # one node blocked is not an outage
    ({"a": forbidden, "b": forbidden, "c": ok}, "down"),
    ({"a": timeout, "b": timeout, "c": timeout}, "down"),
    ({"a": ok, "b": None, "c": None}, "unknown"),           # too few answers to judge
    ({}, "unknown"),
]
bad = 0
for results, want in cases:
    got = verdict(results)
    print(("PASS" if got == want else "FAIL"), want, got)
    bad += got != want
sys.exit(1 if bad else 0)
