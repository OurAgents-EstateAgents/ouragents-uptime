#!/usr/bin/env python3
"""Alert when ouragents.co.uk stops loading.

The pages are loaded every 5 minutes by a scheduled job in Supabase (the
website host's firewall blocks GitHub's servers, but not Supabase's). This
script reads those results and fails when a page failed twice in a row,
when results are missing, or when the latest results are more than 15
minutes old. Emails go to the owner through Brevo's SMTP relay: on the
first failure, hourly while down, on recovery, and a short "still
watching" note every Monday morning (which also keeps the Brevo key in use).
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


def weekly_due(now):
    return now.weekday() == 0 and now.hour == 8 and now.minute < 5


SUBJECTS = {
    "down": ("WEBSITE DOWN: ouragents.co.uk is not loading",
             "Our automatic check could not load the website from outside your network."),
    "up": ("Website back up: ouragents.co.uk is loading again",
           "The website is loading normally again."),
    "weekly": ("Weekly: website check is running",
               "Just to confirm the automatic website check is still running. Nothing needs doing."),
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
