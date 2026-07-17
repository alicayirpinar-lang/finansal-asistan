# Finansal Asistan (v1)

Kişisel finansal fırsat radarı — tam plan: `../finansal-asistan-plan.md`

## Kurulum

```
pip install -r requirements.txt
copy .env.example .env    # sonra .env içini doldur
```

### Gerekli hesaplar (hepsi ücretsiz)
1. **Gemini API anahtarı** — https://aistudio.google.com/apikey → "Create API key" → `GEMINI_API_KEY`
2. **Telegram bot** — Telegram'da @BotFather → `/newbot` → token'ı `TELEGRAM_BOT_TOKEN`'a.
   Chat ID için: bota bir mesaj at, sonra tarayıcıda
   `https://api.telegram.org/bot<TOKEN>/getUpdates` aç → `"chat":{"id":...}` → `TELEGRAM_CHAT_ID`
3. **Supabase** — https://supabase.com → yeni proje → SQL Editor'de `db/schema.sql`'i çalıştır.
   Project Settings → API: URL → `SUPABASE_URL`, `service_role` key → `SUPABASE_KEY`

## Kullanım

```
python main.py                 # pipeline: haber -> filtre -> AI tez -> Telegram
python manage.py durum         # açık pozisyonlar
python manage.py tezler        # açık tezler
python manage.py ekle --tur deneme --sembol USO --adet 10 --fiyat 78.5 --tarih 2026-07-17
python manage.py kapat --sembol USO
```

## v1 kapsamı
- ~30 sembol (BIST 15 + ABD 15), tema bazlı RSS tarama
- Taslak zincir + red-team (8 soru) + kod tabanlı birleştirme
- Telegram bildirimi (kritik/orta), gözlem sadece DB'ye
- Deneme/gerçek portföy ayrımı (CLI üzerinden)

Sonraki fazlar (plan bölüm 15): buluta taşıma, tez takibi, teknik sinyaller,
kritik hızlı yol, geniş tarama, dashboard.
