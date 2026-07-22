-- Tez zamanlaması: "beklenen kaç gündü" artık kalıcı yazılıyor (kod her zaman
-- hesaplıyordu ama sadece anlık karar için kullanıp atıyordu — sapma
-- ölçülemiyordu). Gerçekleşen gün resolved_at - created_at'ten hesaplanır,
-- ayrı kolon gerekmez.
alter table theses add column if not exists expected_horizon_days int;

-- Ayarlar sayfası: son kaydetme zamanını göstermek için.
alter table user_settings add column if not exists updated_at timestamptz;
