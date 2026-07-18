-- Analitik motor (faz 11): teknik analiz vektörü + engel oranı ayarları.
-- technical_signals.analiz: günlük gösterge vektörü + kurulum etiketleri (jsonb)
alter table technical_signals add column if not exists analiz jsonb;

-- Engel oranı (hurdle): tezin yıllık eşdeğeri bunları yenmiyorsa tez açılmaz.
-- enflasyon_yillik: TÜİK yıllık TÜFE (Haziran 2026: %32.11) — ayda bir güncelle.
-- mevduat_yillik: bankanın güncel TL mevduat faizi — kullanıcı doldurur.
alter table user_settings add column if not exists enflasyon_yillik numeric;
alter table user_settings add column if not exists mevduat_yillik numeric;
update user_settings set enflasyon_yillik = 32.11 where id = 1 and enflasyon_yillik is null;
