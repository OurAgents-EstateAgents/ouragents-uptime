#!/usr/bin/env python3
"""Check that each URL loads for real visitors.

GitHub's own servers are blocked by the website host's firewall, so the
check is made through check-host.net, which loads the page from several
servers in different countries. A URL counts as down only when at least
three servers answered and fewer than half of them got HTTP 200. A down
URL is checked again after RETRY_WAIT seconds before it is reported.

Exit 0 = up (or the outside service could not give an answer), 1 = down.
"""
import json, os, sys, time, urllib.parse, urllib.request

API = "https://check-host.net"
NODES = int(os.environ.get("NODES", "4"))
UA = "OurAgentsUptimeCheck/1.0 (+https://github.com/OurAgents-EstateAgents/ouragents-uptime)"
RETRY_WAIT = int(os.environ.get("RETRY_WAIT", "60"))


def verdict(results):
    """results: check-host result map {node: [[ok, time, msg, code, ip]] or None}."""
    answered = [r[0] for r in results.values() if r and r[0]]
    if len(answered) < 3:
        return "unknown"
    up = sum(1 for r in answered if len(r) > 3 and r[3] == "200")
    return "up" if up * 2 >= len(answered) else "down"


def _get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def outside_check(url):
    try:
        q = urllib.parse.urlencode({"host": url, "max_nodes": NODES})
        rid = _get(f"{API}/check-http?{q}")["request_id"]
        results = {}
        for _ in range(10):
            time.sleep(4)
            results = _get(f"{API}/check-result/{rid}")
            if all(v is not None for v in results.values()):
                break
        return verdict(results), results
    except Exception as exc:  # outside service failed: no verdict
        return "unknown", {"error": str(exc)}


def summary(results):
    out = []
    for node, r in results.items():
        if node == "error":
            out.append(f"error: {r}")
        elif r and r[0]:
            out.append(f"{node.split('.')[0]}={r[0][3] or r[0][2]}")
        else:
            out.append(f"{node.split('.')[0]}=no answer")
    return ", ".join(out)


def main(urls):
    down = False
    for url in urls:
        state, results = outside_check(url)
        if state == "down":
            time.sleep(RETRY_WAIT)
            state, results = outside_check(url)
        label = {"up": "UP  ", "down": "DOWN", "unknown": "??  "}[state]
        print(f"{label} {url}  [{summary(results)}]", flush=True)
        down = down or state == "down"
    return 1 if down else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
