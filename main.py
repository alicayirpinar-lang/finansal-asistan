"""v1 pipeline: haber topla -> filtrele -> finansal beyin -> kaydet -> bildir.

Çalıştırma: python main.py
"""
import os
import sys
import traceback

from dotenv import load_dotenv

load_dotenv()

from config import SYMBOLS, MAX_THESES_PER_RUN
from src import collector, filter as f1, brain, prices, storage, notifier


def run():
    cap = int(os.environ.get("DAILY_GEMINI_CAP", "40"))

    print("Semboller senkronlanıyor...")
    storage.ensure_symbols(SYMBOLS)

    print("Haberler toplanıyor...")
    items, errors = collector.collect_news()
    print(f"  {len(items)} haber, {len(errors)} kaynak hatası")
    for name, err in errors:
        print(f"  ! {name}: {err[:100]}")
    if not items:
        print("Hiç haber yok, çıkılıyor.")
        return

    clusters = f1.dedup(items)
    print(f"  dedup: {len(items)} haber -> {len(clusters)} küme")

    portfolio_syms = storage.open_portfolio_symbols()
    events = f1.build_events(clusters, portfolio_syms)
    print(f"  {len(events)} skorlu olay adayı")

    produced = 0
    for event in events:
        if produced >= MAX_THESES_PER_RUN:
            break
        used = storage.gemini_calls_today()
        if used + 2 > cap:
            print(f"Günlük Gemini tavanı doldu ({used}/{cap}) — kalan olaylar arşivleniyor (kuyruklanmaz).")
            break
        if storage.recent_thesis_exists(event["symbol"]):
            continue  # aynı sembolde 48 saat içinde tez var: mükerrer önleme
        try:
            print(f'\n[{event["symbol"]}] {event["title"][:80]}...')
            draft = brain.draft_chain(event)
            storage.log_gemini_call("taslak")
            redteam = brain.red_team(event, draft)
            storage.log_gemini_call("redteam")
            final, tier, status = brain.merge(event, draft, redteam)
            # Referans fiyat + stop (2×ATR) — tez takibi bunlarla çalışır (plan bölüm 7)
            entry_ref = prices.current_price(event["symbol"], event["market"])
            if entry_ref:
                atr = prices.atr14(event["symbol"], event["market"])
                if atr:
                    sign = 1 if draft["yon"] == "yukselis" else -1
                    inv = redteam.setdefault("gecersiz_kilma_kosulu", {})
                    inv["stop_fiyat"] = round(entry_ref - sign * 2 * atr, 2)
            thesis = storage.insert_thesis(event, draft, redteam, final, tier, status,
                                           entry_price_ref=entry_ref)
            produced += 1
            print(f"  -> güven={final}, katman={tier}, durum={status}")
            if status == "acik" and tier in ("kritik", "orta"):
                notifier.send(notifier.format_thesis(event, draft, redteam, final, tier))
                print("  -> Telegram bildirimi gönderildi")
        except Exception:
            print(f'  ! {event["symbol"]} işlenirken hata (pipeline devam ediyor):')
            traceback.print_exc(limit=2)

    print(f"\nBitti: {produced} tez üretildi. Bugünkü Gemini kullanımı: {storage.gemini_calls_today()}")


if __name__ == "__main__":
    missing = [k for k in ("GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN",
                           "TELEGRAM_CHAT_ID", "SUPABASE_URL", "SUPABASE_KEY")
               if not os.environ.get(k)]
    if missing:
        print("Eksik .env değişkenleri:", ", ".join(missing))
        print(".env.example dosyasını .env olarak kopyalayıp doldur.")
        sys.exit(1)
    run()
