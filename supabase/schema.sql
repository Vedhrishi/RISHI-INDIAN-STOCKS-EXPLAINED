-- RISHI | Indian Stocks Explained: Supabase schema (run once in Supabase SQL editor, then run seed.sql)
create table if not exists episodes (
  ep int not null,
  part int not null,
  title text not null,
  series_title text,
  publish_at timestamp,            -- IST posting time
  thumb text,
  youtube_url text,
  instagram_url text,
  facebook_url text,
  primary key (ep, part)
);

create table if not exists course_waitlist (
  id bigint generated always as identity primary key,
  email text not null,
  created_at timestamptz default now()
);

alter table episodes enable row level security;
alter table course_waitlist enable row level security;

-- anyone can read released episodes
create policy "public read released episodes" on episodes
  for select using (publish_at <= (now() at time zone 'Asia/Kolkata'));

-- anyone can join the waitlist, nobody can read it from the browser
create policy "public join waitlist" on course_waitlist
  for insert with check (email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$');
