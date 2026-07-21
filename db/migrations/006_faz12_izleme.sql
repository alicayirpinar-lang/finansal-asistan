-- Faz 12 B: ikinci derece akıl yürütme — füzyon şartını geçemeyen (teknik
-- destek yok) bağlar tez olmaz, izleme listesine düşer. Teknik kurulunca
-- (main.py her koşuda kontrol eder) tam teze döner; süresi dolarsa düşer.
create table if not exists ikinci_derece_izleme (
  id uuid primary key default gen_random_uuid(),
  symbol text references symbols(symbol),
  market text,
  yon text check (yon in ('yukselis','dusus')),
  mekanizma text,
  guven text check (guven in ('dusuk','orta','yuksek')),
  kaynak_baslik text,
  kaynak_url text,
  status text default 'bekliyor' check (status in ('bekliyor','teyit_edildi','suresi_doldu')),
  created_at timestamptz default now(),
  resolved_at timestamptz
);
