-- Faz 12: fırsat kaynaklarını çeşitlendirme. Her teze kaynak alanı eklenir
-- (haber/teknik/ikinci_derece/geriye_donuk) — isabet karnesi motor bazlı ölçülebilsin.
alter table theses add column if not exists kaynak text default 'haber'
  check (kaynak in ('haber', 'teknik', 'ikinci_derece', 'geriye_donuk'));

-- kaynak SONA eklendi: Postgres CREATE OR REPLACE VIEW mevcut sütunların
-- pozisyonunu değiştirmeye izin vermiyor (42P16 hatası), sadece sona ekleme.
create or replace view isabet_karnesi as
select category, market, final_confidence,
  count(*) filter (where status='hedefe_ulasti') as basarili,
  count(*) filter (where status='tez_bozuldu') as basarisiz,
  count(*) filter (where status='suresi_doldu') as sonucsuz,
  round(
    count(*) filter (where status='hedefe_ulasti')::numeric /
    nullif(count(*) filter (where status in ('hedefe_ulasti','tez_bozuldu')),0), 2
  ) as isabet_orani,
  kaynak
from theses
where status not in ('taslak','acik','zayiflama_suphesi','iptal_edildi','kullanici_satti')
group by category, market, final_confidence, kaynak;
