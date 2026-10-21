# Our Agents website uptime check

Every 5 minutes a scheduled job in Supabase loads www.ouragents.co.uk (homepage, Morpeth page, blog).
Every 5 minutes this GitHub workflow reads those results. If a page failed twice running, or the
results stop arriving, the run fails and GitHub emails the account owner.

To test the alert: Actions > Website uptime > Run workflow, tick "Fail on purpose".
