-- Finansal Asistan - tam şema (plan bölüm 10)
-- Supabase SQL Editor'de tek seferde çalıştırılır.

create extension if not exists vector;

create table if not exists symbols (
  symbol text primary key,
  name text not null,
  market text not null check (market in ('BIST','US')),
  sector text,
  theme_tags jsonb default '[]',
  updated_at timestamptz default now()
);

create table if not exists news_items (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  title text not null,
  url text,
  published_at timestamptz,
  fetched_at timestamptz default now(),
  language text,
  embedding vector(384),
  cluster_id uuid,
  is_representative boolean default true
);

create table if not exists news_clusters (
  id uuid primary key default gen_random_uuid(),
  representative_news_id uuid references news_items(id),
  source_count int default 1,
  first_seen_at timestamptz,
  category text
);

create table if not exists events (
  id uuid primary key default gen_random_uuid(),
  cluster_id uuid references news_clusters(id),
  symbol text references symbols(symbol),
  market text,
  category text,
  relevance_score numeric,
  priority_lane text check (priority_lane in ('kritik','normal_kuyruk')),
  status text default 'bekliyor',
  created_at timestamptz default now()
);

create table if not exists theses (
  id uuid primary key default gen_random_uuid(),
  event_id uuid references events(id),
  symbol text references symbols(symbol),
  market text,
  category text,
  draft_chain jsonb,
  redteam_output jsonb,
  final_confidence text check (final_confidence in ('dusuk','orta','yuksek')),
  notification_tier text check (notification_tier in ('kritik','orta','gozlem')),
  direction text,
  target_range_pct numrange,
  horizon text,
  invalidation_condition jsonb,
  entry_price_ref numeric,
  event_embedding vector(384),
  status text default 'taslak' check (status in
    ('taslak','acik','zayiflama_suphesi','iptal_edildi',
     'hedefe_ulasti','tez_bozuldu','suresi_doldu','kullanici_satti')),
  created_at timestamptz default now(),
  resolved_at timestamptz,
  resolution_note text
);

create table if not exists thesis_checks (
  id uuid primary key default gen_random_uuid(),
  thesis_id uuid references theses(id),
  checked_at timestamptz default now(),
  price_at_check numeric,
  signal_snapshot jsonb,
  result text
);

create table if not exists kurtarma_degerlendirmeleri (
  id uuid primary key default gen_random_uuid(),
  thesis_id uuid references theses(id),
  triggered_signals jsonb,
  ai_verdict text check (ai_verdict in ('yanlis_alarm','kismi_cikis','tam_cikis')),
  cikis_orani numeric,
  created_at timestamptz default now()
);

create table if not exists portfolio (
  id uuid primary key default gen_random_uuid(),
  symbol text references symbols(symbol),
  market text,
  quantity numeric not null,
  entry_price numeric not null,
  entry_date date not null,
  source text check (source in ('sistem_tezi','disaridan')),
  portfolio_type text not null default 'gercek'
    check (portfolio_type in ('gercek','deneme')),
  thesis_id uuid references theses(id),
  status text default 'acik',
  closed_at timestamptz,
  closed_quantity numeric,
  close_reason text
);

create table if not exists technical_signals (
  id uuid primary key default gen_random_uuid(),
  symbol text references symbols(symbol),
  market text,
  computed_at timestamptz default now(),
  volume_z numeric,
  rsi numeric,
  ma20_cross boolean,
  pct_from_52w numeric,
  signal_count int,
  gozlem_skoru numeric
);

create table if not exists alerts (
  id uuid primary key default gen_random_uuid(),
  type text,
  thesis_id uuid references theses(id),
  sent_at timestamptz default now(),
  telegram_message_id text,
  content_summary text
);

create table if not exists daily_reports (
  id uuid primary key default gen_random_uuid(),
  market text check (market in ('BIST','US')),
  report_date date,
  sections_sent jsonb,
  sent_at timestamptz default now()
);

create table if not exists gemini_usage_log (
  id uuid primary key default gen_random_uuid(),
  date date default current_date,  -- uygulama tarafında Pasifik saatine göre yazılır
  call_type text,
  call_count int default 1,
  created_at timestamptz default now()
);

create table if not exists user_settings (
  id int primary key default 1,
  toplam_sermaye numeric,
  deneme_sermaye numeric,
  temel_risk_pct numeric default 1.0,
  max_tek_pozisyon_pct numeric default 10.0,
  max_tema_pct numeric default 15.0,
  sessiz_saat_baslangic time default '01:00',
  sessiz_saat_bitis time default '08:00',
  gozlem_bolumu_aktif boolean default true,
  check (id = 1)
);

insert into user_settings (id) values (1) on conflict (id) do nothing;

create or replace view isabet_karnesi as
select category, market, final_confidence,
  count(*) filter (where status='hedefe_ulasti') as basarili,
  count(*) filter (where status='tez_bozuldu') as basarisiz,
  count(*) filter (where status='suresi_doldu') as sonucsuz,
  round(
    count(*) filter (where status='hedefe_ulasti')::numeric /
    nullif(count(*) filter (where status in ('hedefe_ulasti','tez_bozuldu')),0), 2
  ) as isabet_orani
from theses
where status not in ('taslak','acik','zayiflama_suphesi','iptal_edildi','kullanici_satti')
group by category, market, final_confidence;
