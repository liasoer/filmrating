
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

-- Empfehlungen unter Freunden (mit Push über die Edge Function "push")
create table if not exists public.recommendations(
  id uuid primary key default gen_random_uuid(),
  from_user uuid not null default auth.uid() references auth.users(id) on delete cascade,
  to_user uuid not null references auth.users(id) on delete cascade,
  key text not null, title text not null, year int, imdb_id text, poster text, ext jsonb, message text,
  status text not null default 'pending' check (status in ('pending','accepted','declined')),
  pushed boolean not null default false, created_at timestamptz not null default now(),
  unique(from_user, to_user, key)
);
alter table public.recommendations enable row level security;
create policy "rec_select" on public.recommendations for select using (auth.uid() = from_user or auth.uid() = to_user);
create policy "rec_insert" on public.recommendations for insert with check (auth.uid() = from_user and exists (select 1 from public.friendships f where f.status = 'accepted' and ((f.requester = from_user and f.addressee = to_user) or (f.requester = to_user and f.addressee = from_user))));
create policy "rec_update" on public.recommendations for update using (auth.uid() = to_user) with check (auth.uid() = to_user);
create policy "rec_delete" on public.recommendations for delete using (auth.uid() = from_user or auth.uid() = to_user);
create or replace function public.rec_push() returns trigger language plpgsql security definer set search_path = public as $$
begin perform net.http_post(url := 'https://vpdgwopcsevtvvaufegr.supabase.co/functions/v1/push', body := jsonb_build_object('type','recommendation','id',new.id), headers := '{"Content-Type": "application/json"}'::jsonb); return new; end $$;
create trigger recommendation_push after insert on public.recommendations for each row execute function public.rec_push();
