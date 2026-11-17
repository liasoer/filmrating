
-- Merkliste (nur für die eigene Person sichtbar)
create table if not exists public.watchlist(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade default auth.uid(),
  key text not null, title text not null, year int, imdb_id text, poster text, ext jsonb,
  created_at timestamptz not null default now(),
  unique(user_id, key)
);
alter table public.watchlist enable row level security;
create policy "watch_select_own" on public.watchlist for select using (auth.uid() = user_id);
create policy "watch_insert_own" on public.watchlist for insert with check (auth.uid() = user_id);
create policy "watch_update_own" on public.watchlist for update using (auth.uid() = user_id);
create policy "watch_delete_own" on public.watchlist for delete using (auth.uid() = user_id);

-- Lebenszeichen gegen die automatische Pause
create table if not exists public.heartbeat(id int primary key default 1, at timestamptz not null default now());
alter table public.heartbeat enable row level security;
create or replace function public.heartbeat() returns timestamptz language sql security definer set search_path = public as $$
  insert into public.heartbeat(id, at) values (1, now()) on conflict (id) do update set at = excluded.at returning at; $$;
grant execute on function public.heartbeat() to anon, authenticated;
