-- 22 Temmuz 2026 ikinci kesinti: kota tavanı BAŞARISIZ denemeleri de saydığı
-- için Google gerçek bir hata (prepay/kota) verince sayaç aniden tavana
-- vurup main.py'yi o günün geri kalanında sessizce hiçbir şey denemez hale
-- getirdi. Tavan artık sadece başarılı çağrıları sayıyor (storage.py).
alter table gemini_usage_log add column if not exists basarili boolean not null default true;
