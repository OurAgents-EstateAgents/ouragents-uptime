#!/usr/bin/env python3
"""Backup watchdog for the website uptime monitor.

Supabase loads the pages every 5 minutes and its uptime-alert function
emails the owner when the site is down. This GitHub job is the backup: it
emails only when Supabase's results are missing or more than 15 minutes
old, i.e. the Supabase monitor itself has stopped. A short "backup check is
running" note goes out on the first Monday of each month, which also keeps
this job's Brevo SMTP key from expiring after 90 idle days.
"""
import json, os, smtplib, sys, urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

SUPABASE_URL = "https://niokqzlfxpelgqqujeuy.supabase.co"
PAGES = 3
STALE = timedelta(minutes=15)
SENDER = "hq@ouragents.co.uk"


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
    return found


def email_kind(prev_failed, now_failed, minute):
    """Which email to send: "down" when the site first fails and once an hour
    while it stays down, "up" when it recovers, otherwise None."""
    if now_failed:
        return "down" if (not prev_failed or minute < 5) else None
    return "up" if prev_failed else None


def weekly_due(now):
    """Monthly backup heartbeat: first Monday of the month, 09:00-09:59 UTC."""
    return now.weekday() == 0 and now.day <= 7 and now.hour == 9


SUBJECTS = {
    "down": ("WEBSITE CHECK STOPPED: ouragents.co.uk is no longer being watched",
             "The automatic website check in Supabase has stopped reporting, so a real outage would not be noticed. Please ask Claude to look at it."),
    "up": ("Website check running again",
           "The automatic website check in Supabase is reporting again."),
    "weekly": ("Monthly: backup website check is running",
               "Just to confirm the backup website check is still running. Nothing needs doing."),
}


def send_email(kind, lines):
    login, key = os.environ.get("BREVO_SMTP_LOGIN", ""), os.environ.get("BREVO_SMTP_KEY", "")
    if not (login and key):
        print("No BREVO_SMTP_LOGIN / BREVO_SMTP_KEY secrets yet - email not sent.")
        return
    subject, intro = SUBJECTS[kind]
    msg = EmailMessage()
    msg["From"] = f"Our Agents website check <{SENDER}>"
    msg["To"] = os.environ.get("ALERT_TO", SENDER)
    msg["Subject"] = subject
    msg.set_content(intro + "\n\n" + "\n".join("- " + l for l in lines) +
                    "\n\nChecks run every 5 minutes: https://github.com/OurAgents-EstateAgents/ouragents-uptime/actions\n")
    with smtplib.SMTP("smtp-relay.brevo.com", 587, timeout=30) as s:
        s.starttls()
        s.login(login, key)
        s.send_message(msg)
    print(f"Email ({kind}) sent to {msg['To']}")


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
    kind = email_kind(prev_failed, bool(found), now.minute)
    if kind:
        send_email(kind, found or ["All 3 pages are loading."])
    elif not found and weekly_due(now):
        send_email("weekly", ["All 3 pages are loading."])
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
