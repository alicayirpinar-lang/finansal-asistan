-- 31 Temmuz 2026 bulgusu: 28 Temmuz'daki "aynı sembolde farklı URL'ye izin ver"
-- düzeltmesi (migration 012) bir yan etki doğurdu — aynı gerçek olayı (ör. bir
-- bilanço haberi) 5 farklı kaynak 5 farklı URL'yle işleyince sistem bunu 5 AYRI
-- tez sandı (AMZN vakası: aynı giriş fiyatı 235.5, 10 saat içinde 5 tez, hepsi
-- aynı sonuçla kapandı). Artık URL'nin yanı sıra başlık benzerliği de (dedup()
-- ile aynı rapidfuzz eşiği) kontrol ediliyor — aynı olayın farklı kaynaktan
-- gelmesi yeni bir tez AÇMAZ, mevcut tezin dogrulama_sayisi'nı artırır (çoklu
-- kaynak doğrulaması kaybolmaz, sadece tekilleşir — bkz. storage.tez_kilitli_mi).
alter table theses add column if not exists kaynak_baslik text;
alter table theses add column if not exists dogrulama_sayisi int not null default 0;
