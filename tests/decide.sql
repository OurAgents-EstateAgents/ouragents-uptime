-- Tests for the Supabase alert rules. Run in the Supabase SQL editor; every row must show ok = true.
with t(name, got, want) as (values
 ('all up',        cardinality(public.uptime_problems('[{"url":"a","last_status":200,"prev_status":200,"last_checked":"2026-10-21T23:00:00Z"},{"url":"b","last_status":200,"prev_status":200,"last_checked":"2026-10-21T23:00:00Z"},{"url":"c","last_status":200,"prev_status":200,"last_checked":"2026-10-21T23:00:00Z"}]', '2026-10-21T23:03:00Z'))::text, '0'),
 ('one blip',      cardinality(public.uptime_problems('[{"url":"a","last_status":503,"prev_status":200,"last_checked":"2026-10-21T23:00:00Z"},{"url":"b","last_status":200,"prev_status":200,"last_checked":"2026-10-21T23:00:00Z"},{"url":"c","last_status":200,"prev_status":200,"last_checked":"2026-10-21T23:00:00Z"}]', '2026-10-21T23:03:00Z'))::text, '0'),
 ('down twice',    cardinality(public.uptime_problems('[{"url":"a","last_status":403,"prev_status":403,"last_checked":"2026-10-21T23:00:00Z"},{"url":"b","last_status":200,"prev_status":200,"last_checked":"2026-10-21T23:00:00Z"},{"url":"c","last_status":200,"prev_status":200,"last_checked":"2026-10-21T23:00:00Z"}]', '2026-10-21T23:03:00Z'))::text, '1'),
 ('no answer x2',  cardinality(public.uptime_problems('[{"url":"a","last_status":null,"last_error":"timed out","prev_status":null,"last_checked":"2026-10-21T23:00:00Z"},{"url":"b","last_status":200,"prev_status":200,"last_checked":"2026-10-21T23:00:00Z"},{"url":"c","last_status":200,"prev_status":200,"last_checked":"2026-10-21T23:00:00Z"}]', '2026-10-21T23:03:00Z'))::text, '1'),
 ('stale',         cardinality(public.uptime_problems('[{"url":"a","last_status":200,"prev_status":200,"last_checked":"2026-10-21T22:30:00Z"},{"url":"b","last_status":200,"prev_status":200,"last_checked":"2026-10-21T23:00:00Z"},{"url":"c","last_status":200,"prev_status":200,"last_checked":"2026-10-21T23:00:00Z"}]', '2026-10-21T23:03:00Z'))::text, '1'),
 ('empty',         cardinality(public.uptime_problems('[]', '2026-10-21T23:03:00Z'))::text, '1'),
 ('first down',    coalesce(public.uptime_email_kind(true,  false, null, null, '2026-10-21T23:03:00Z'), '-'), 'down'),
 ('still down',    coalesce(public.uptime_email_kind(true,  true, '2026-10-21T22:50:00Z', null, '2026-10-21T23:03:00Z'), '-'), '-'),
 ('hourly remind', coalesce(public.uptime_email_kind(true,  true, '2026-10-21T22:00:00Z', null, '2026-10-21T23:03:00Z'), '-'), 'down'),
 ('back up',       coalesce(public.uptime_email_kind(false, true, '2026-10-21T22:00:00Z', null, '2026-10-21T23:03:00Z'), '-'), 'up'),
 ('quiet',         coalesce(public.uptime_email_kind(false, false, null, null, '2026-10-21T23:03:00Z'), '-'), '-'),
 ('weekly mon 8',  coalesce(public.uptime_email_kind(false, false, null, null, '2026-10-26T08:03:00Z'), '-'), 'weekly'),
 ('weekly once',   coalesce(public.uptime_email_kind(false, false, null, '2026-10-26', '2026-10-26T08:08:00Z'), '-'), '-'),
 ('not tuesday',   coalesce(public.uptime_email_kind(false, false, null, null, '2026-10-27T08:03:00Z'), '-'), '-'))
select name, got = want as ok, got from t;
