# Our Agents website uptime check

**Main monitor (Supabase project `ouragents`):** every 5 minutes the cron job `website-uptime` loads
www.ouragents.co.uk (homepage, Morpeth page, blog) and keeps the results in `uptime_checks`.
Two minutes later the cron job `website-uptime-alert` calls the edge function `uptime-alert`
(source in `supabase/functions/uptime-alert/`), which asks `uptime_decide()` whether an email is due
and sends it to hq@ouragents.co.uk through Brevo's SMTP relay: when a page fails twice running,
hourly while it stays down, when it is back, and a short "still running" note on Monday mornings.
The decision rules are tested in `tests/decide.sql`.

**Backup (this GitHub workflow):** runs on GitHub's schedule (irregular, roughly hourly) and emails
only if the Supabase results stop arriving, plus a monthly "backup is running" note.
GitHub's own servers cannot load the website (blocked by the host's firewall), so it never checks the
site directly. Secrets: SUPABASE_KEY, BREVO_SMTP_LOGIN, BREVO_SMTP_KEY.

To test the backup email: Actions > Website uptime backup > Run workflow, tick "Fail on purpose".
