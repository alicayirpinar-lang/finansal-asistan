-- Kritik hızlı yol dedup tablosu: aynı kritik başlık iki kez tetiklemez.
-- Edge Function her koşuda 7 günden eski kayıtları kendisi temizler.
create table if not exists critical_seen (
  id uuid primary key default gen_random_uuid(),
  title_norm text unique,
  title text,
  created_at timestamptz default now()
);
