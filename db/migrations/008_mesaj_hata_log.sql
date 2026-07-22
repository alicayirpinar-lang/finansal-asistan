-- Mesajlaşma merkezi + hata sayfası (22 Temmuz 2026, Gemini kesintisinin
-- 12+ saat fark edilmeden sürmesinden çıkarılan ders — sistem sessizce
-- bozulabiliyor, görünürlük yoktu).

-- notifier.send() üzerinden giden HER mesaj (başarılı/başarısız) buraya yazılır.
create table if not exists mesaj_log (
  id uuid primary key default gen_random_uuid(),
  tur text not null,
  icerik text,
  basarili boolean not null default true,
  telegram_message_id text,
  hata_metni text,
  created_at timestamptz default now()
);

-- Merkezi hata kaydı: mevcut try/except bloklarına bağlanır.
create table if not exists sistem_hatalari (
  id uuid primary key default gen_random_uuid(),
  kaynak text not null,
  mesaj text,
  detay text,
  seviye text not null default 'normal' check (seviye in ('normal', 'kritik')),
  created_at timestamptz default now()
);

create index if not exists mesaj_log_created_idx on mesaj_log (created_at desc);
create index if not exists sistem_hatalari_created_idx on sistem_hatalari (created_at desc);
