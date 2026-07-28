-- 28 Temmuz 2026 bulgusu: recent_thesis_exists() sembol bazında kördü — aynı
-- sembolde son 48 saatte HERHANGİ bir tez varsa, o sembolde çıkan FARKLI/yeni
-- bir katalizörü de (örn. TSLA'nın bir önceki gün faiz haberiyle tez almışken
-- ertesi gün gelen bilanço haberi) tamamen engelliyordu. Artık hangi haberin
-- (URL) tezi ürettiği saklanıyor — main.py aynı haberin tekrarını hâlâ
-- engeller ama farklı bir URL'den gelen yeni olaya izin verir (bkz.
-- storage.tez_kilitli_mi).
alter table theses add column if not exists kaynak_url text;
