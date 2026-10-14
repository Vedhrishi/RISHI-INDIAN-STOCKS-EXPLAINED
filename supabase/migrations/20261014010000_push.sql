-- Web Push subscribers. Browsers may add themselves; only the server (holding the push secret) can list/remove.
create table if not exists push_subscriptions (endpoint text primary key, sub jsonb not null, created_at timestamptz default now());
create table if not exists push_sent (key text primary key, sent_at timestamptz default now());
create table if not exists app_secrets (name text primary key, value text not null);
alter table push_subscriptions enable row level security;
alter table push_sent enable row level security;
alter table app_secrets enable row level security;
create policy "anyone can subscribe" on push_subscriptions for insert with check (endpoint like 'https://%');

create or replace function push_ok(p_secret text) returns boolean language sql security definer as
$$ select exists (select 1 from app_secrets where name = 'push' and value = p_secret) $$;
create or replace function push_list(p_secret text) returns setof jsonb language plpgsql security definer as
$$ begin if not push_ok(p_secret) then raise exception 'denied'; end if; return query select sub from push_subscriptions; end $$;
create or replace function push_remove(p_secret text, p_endpoint text) returns void language plpgsql security definer as
$$ begin if not push_ok(p_secret) then raise exception 'denied'; end if; delete from push_subscriptions where endpoint = p_endpoint; end $$;
create or replace function push_claim(p_secret text, p_key text) returns boolean language plpgsql security definer as
$$ declare n int; begin if not push_ok(p_secret) then raise exception 'denied'; end if;
  insert into push_sent(key) values (p_key) on conflict do nothing; get diagnostics n = row_count; return n > 0; end $$;
