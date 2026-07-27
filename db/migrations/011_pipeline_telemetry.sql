-- 27 Temmuz 2026 bulgusu: "neden hala tez yok" sorusuna cevap vermek için
-- her seferinde GitHub Actions loglarını elle kazımak gerekiyordu (haber
-- sayısı, küme sayısı, eşleşen küme, skoru geçen olay sayısı hiçbir yerde
-- saklanmıyordu). Huninin her aşamasını tek satırda kaydeden bu tablo,
-- direkt-eşleşme tazelik düzeltmesinin (ve gelecekteki her değişikliğin)
-- gerçek etkisini bir SQL sorgusuyla ölçülebilir yapar.
create table if not exists pipeline_calistirmalari (
  id uuid primary key default gen_random_uuid(),
  haber_sayisi int,
  kume_sayisi int,
  eslesen_kume int,
  event_cifti_toplam int,
  event_cifti_gecti int,
  triaj_batch int,
  triaj_elenen int,
  draft_reddetti int,
  redteam_iptal int,
  acik_uretilen int,
  gemini_basarili int,
  gemini_toplam int,
  created_at timestamptz default now()
);
create index if not exists pipeline_calistirmalari_created_idx on pipeline_calistirmalari(created_at);
