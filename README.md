# Our Agents website uptime check

Every 5 minutes a scheduled job in Supabase loads www.ouragents.co.uk (homepage, Morpeth page, blog).
Every 5 minutes this GitHub workflow reads those results. If a page failed twice running, or the
results stop arriving, it emails hq@ouragents.co.uk through Brevo: straight away, then once an hour
while the site stays down, and once more when it is back.

Needs the repository secrets SUPABASE_KEY (Supabase publishable key) and BREVO_API_KEY.

To test the alert: Actions > Website uptime > Run workflow, tick "Fail on purpose".
