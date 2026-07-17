-- Geriye dönük tez kuyruğu (plan bölüm 8): dashboard'dan "dışarıdan" girilen
-- pozisyon için kullanıcı isterse tez talebi buraya düşer; Python tarama turu
-- (main.py) işler, tez pozisyona geri yazılır.
create table if not exists retro_thesis_queue (
  id uuid primary key default gen_random_uuid(),
  position_id uuid references portfolio(id),
  symbol text,
  status text default 'bekliyor' check (status in ('bekliyor','islendi','tez_bulunamadi')),
  note text,
  created_at timestamptz default now(),
  processed_at timestamptz
);
