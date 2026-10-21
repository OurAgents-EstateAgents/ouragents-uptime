#!/usr/bin/env python3
"""Alert when ouragents.co.uk stops loading.

The pages are loaded every 5 minutes by a scheduled job in Supabase (the
website host's firewall blocks GitHub's servers, but not Supabase's). This
script reads those results and exits 1 - which makes GitHub email the
owner - when a page failed twice in a row, when results are missing, or
when the latest results are more than 15 minutes old.
"""
import json, os, sys, urllib.error, urllib.request
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


def email_kind(prev_failed, now_failed, minute):
    """Which email to send: "down" when the site first fails and once an hour
    while it stays down, "up" when it recovers, otherwise None."""
    if now_failed:
        return "down" if (not prev_failed or minute < 5) else None
    return "up" if prev_failed else None


def send_email(kind, lines):
    key = os.environ.get("BREVO_API_KEY", "")
    if not key:
        print("No BREVO_API_KEY secret yet - alert email not sent.")
        return
    to = [{"email": a.strip()} for a in os.environ.get("ALERT_TO", "hq@ouragents.co.uk").split(",") if a.strip()]
    if kind == "down":
        subject = "WEBSITE DOWN: ouragents.co.uk is not loading"
        intro = "Our automatic check could not load the website from outside your network."
    else:
        subject = "Website back up: ouragents.co.uk is loading again"
        intro = "The website is loading normally again."
    body = "<p>" + intro + "</p><ul>" + "".join(f"<li>{l}</li>" for l in lines) + "</ul>"
    payload = {"sender": {"name": "Our Agents website check", "email": "hq@ouragents.co.uk"},
               "to": to, "subject": subject, "htmlContent": body}
    req = urllib.request.Request("https://api.brevo.com/v3/smtp/email", data=json.dumps(payload).encode(),
                                 method="POST", headers={"api-key": key, "Content-Type": "application/json",
                                                         "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"Alert email ({kind}) sent, Brevo status {resp.status}")
    except urllib.error.HTTPError as exc:
        print(f"Alert email ({kind}) NOT sent: Brevo said {exc.code} {exc.read().decode()[:300]}")
        raise


def keep_key_alive():
    """Brevo switches off keys unused for 90 days; touch it once a day."""
    key = os.environ.get("BREVO_API_KEY", "")
    if not key:
        return
    req = urllib.request.Request("https://api.brevo.com/v3/account",
                                 headers={"api-key": key, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"Brevo key checked, status {resp.status}")
    except urllib.error.HTTPError as exc:
        print(f"WARNING: Brevo key check failed: {exc.code} {exc.read().decode()[:200]}")


def fetch(key):
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/rpc/uptime_status", data=b"{}", method="POST",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main():
    now = datetime.now(timezone.utc)
    prev_failed = os.environ.get("PREV_CONCLUSION") == "failure"
    if os.environ.get("FORCE_ALERT") == "true":
        found = ["TEST ALERT: started by hand to check that this email arrives. The website is fine."]
        prev_failed = False
    else:
        rows = fetch(os.environ["SUPABASE_KEY"])
        for r in rows:
            print(f"{'UP  ' if is_up(r['last_status']) else 'DOWN'} {r['last_status'] or r['last_error']} "
                  f"{r['url']} (checked {r['last_checked'][11:16]} UTC)")
        found = problems(rows, now)
    for p in found:
        print("ALERT:", p)
    if now.hour == 6 and now.minute < 5:
        keep_key_alive()
    kind = email_kind(prev_failed, bool(found), now.minute)
    if kind:
        send_email(kind, found or ["All 3 pages are loading."])
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
