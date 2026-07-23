-- 23 Temmuz 2026 bulgusu: her koşu haberleri sıfırdan topluyor, reddedilen bir
-- olay bir daha "denendi" diye işaretlenmiyor — aynı yüksek-skorlu ~25 aday
-- (çoğu rutin KAP bildirimi) her ~15 dakikada bir yeniden triyaja/taslağa
-- gidip yeniden reddediliyor, 146+ adaylık havuzun geri kalanı sıraya hiç
-- giremiyor. ikinci_derece_izleme'deki 22 Temmuz düzeltmesiyle aynı desen:
-- reddedilen (symbol,url) çiftini kaydet, main.py bir daha denemeden önce
-- kontrol eder.
create table if not exists triaj_denemeleri (
  id uuid primary key default gen_random_uuid(),
  symbol text references symbols(symbol),
  url text not null,
  sonuc text check (sonuc in ('triaj_eledi','taslak_reddetti')),
  neden text,
  created_at timestamptz default now()
);
create index if not exists triaj_denemeleri_url_idx on triaj_denemeleri(url);
