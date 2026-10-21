-- Hardening (21 Oct 2026): least privilege, input limits, safe security-definer functions.

-- 1. Browser roles can never write episode data or touch the secrets/sent tables directly.
revoke insert, update, delete, truncate on episodes from anon, authenticated;
revoke all on app_secrets from anon, authenticated;
revoke all on push_sent from anon, authenticated;
revoke select, update, delete on push_subscriptions from anon, authenticated;
revoke select, update, delete on course_waitlist from anon, authenticated;

-- 2. Input limits so the public insert policies cannot be used to fill the database.
alter table course_waitlist drop constraint if exists waitlist_email_len;
alter table course_waitlist add constraint waitlist_email_len check (char_length(email) between 5 and 254);
create unique index if not exists course_waitlist_email_uq on course_waitlist (lower(email));

alter table push_subscriptions drop constraint if exists push_sub_size;
alter table push_subscriptions add constraint push_sub_size
  check (char_length(endpoint) <= 1000 and octet_length(sub::text) <= 4000);

-- 3. Security-definer functions: fixed search_path, no PUBLIC execute beyond what the cron job needs.
alter function push_ok(text) set search_path = public, pg_temp;
alter function push_list(text) set search_path = public, pg_temp;
alter function push_remove(text, text) set search_path = public, pg_temp;
alter function push_claim(text, text) set search_path = public, pg_temp;
revoke execute on function push_ok(text) from public, anon, authenticated;

-- 4. Strip the remaining unneeded table privileges (TRUNCATE ignores RLS, so it must not be granted).
revoke truncate, references, trigger on episodes, course_waitlist, push_subscriptions, push_sent, app_secrets from anon, authenticated;
