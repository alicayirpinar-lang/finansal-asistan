-- Getiri metrikleri (plan bölüm 7.4): XIRR, expectancy, benchmark.
-- close_price: satış fiyatı olmadan gerçekleşen K/Z hesaplanamaz (eksikti).
alter table portfolio add column if not exists close_price numeric;

-- Her rapor turunda anlık görüntü yazılır; dashboard son kaydı okur,
-- birikince trend grafiği bu tablodan beslenir.
create table if not exists portfolio_metrics (
  id uuid primary key default gen_random_uuid(),
  scope text not null check (scope in ('gercek','deneme','tezler')),
  metrics jsonb not null,
  computed_at timestamptz default now()
);
