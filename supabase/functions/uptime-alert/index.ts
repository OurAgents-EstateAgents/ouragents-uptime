// Website-down alert for ouragents.co.uk. Called every 5 minutes by pg_cron.
// public.uptime_decide() says whether an email is due (first failure, hourly
// while down, back up, Monday-morning "still running"); this sends it through
// Brevo's SMTP relay and records it with public.uptime_record().
// Secrets (Edge Function secrets): BREVO_SMTP_LOGIN, BREVO_SMTP_KEY.
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.45.4";
import nodemailer from "npm:nodemailer@6.9.15";

const TO = "hq@ouragents.co.uk";
const SUBJECTS: Record<string, [string, string]> = {
  down: ["WEBSITE DOWN: ouragents.co.uk is not loading",
         "Our automatic check could not load the website from outside your network."],
  up: ["Website back up: ouragents.co.uk is loading again", "The website is loading normally again."],
  weekly: ["Weekly: website check is running",
           "Just to confirm the automatic website check is still running. Nothing needs doing."],
  test: ["TEST: website-down alert", "This is a test of the website-down alert. The website is fine."],
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

async function send(kind: string, lines: string[]) {
  const user = Deno.env.get("BREVO_SMTP_LOGIN"), pass = Deno.env.get("BREVO_SMTP_KEY");
  if (!user || !pass) throw new Error("BREVO_SMTP_LOGIN / BREVO_SMTP_KEY secrets are not set");
  const [subject, intro] = SUBJECTS[kind];
  const t = nodemailer.createTransport({ host: "smtp-relay.brevo.com", port: 465, secure: true, auth: { user, pass } });
  await t.sendMail({
    from: `Our Agents website check <${TO}>`, to: TO, subject,
    text: `${intro}\n\n${lines.map((l) => "- " + l).join("\n")}\n\nThe website is checked every 5 minutes.\n`,
  });
}

Deno.serve(async (req) => {
  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const body = await req.json().catch(() => ({}));
  try {
    if (body.test) {
      const { data: ok } = await db.rpc("uptime_claim_test");
      if (!ok) return json({ sent: false, reason: "a test was already sent in the last hour" }, 429);
      await send("test", ["Sent on request to check the alert email arrives."]);
      return json({ sent: "test" });
    }
    const { data, error } = await db.rpc("uptime_decide");
    if (error) throw error;
    const { failed, kind, lines } = data[0];
    if (kind) await send(kind, lines);
    const rec = await db.rpc("uptime_record", { p_failed: failed, p_sent_kind: kind });
    if (rec.error) throw rec.error;
    return json({ failed, sent: kind ?? null });
  } catch (e) {
    console.error("uptime-alert:", String(e));
    return json({ error: String(e) }, 500);
  }
});
