"""v1 pipeline: haber topla -> filtrele -> finansal beyin -> kaydet -> bildir.

Çalıştırma: python main.py
"""
import os
import sys
import traceback

from dotenv import load_dotenv

load_dotenv()

from config import SYMBOLS, MAX_THESES_PER_RUN
from src import collector, filter as f1, brain, prices, retro, storage, notifier


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

    # Geriye dönük tez talepleri (dashboard köprüsü) — kullanıcı talebi
    # olduğu için normal olaylardan ÖNCE, kota önceliğiyle işlenir.
    try:
        retro.process_queue(clusters, cap)
    except Exception:
        print("Geriye dönük tez kuyruğu hatası (pipeline devam ediyor):")
        traceback.print_exc(limit=2)

    portfolio_syms = storage.open_portfolio_symbols()
    events = f1.build_events(clusters, portfolio_syms)
    print(f"  {len(events)} skorlu olay adayı")

    # Triage: normal kuyruk toplu ön elemeden geçer (1 Gemini çağrısı, tez
    # kalitesi fazı); kritik hızlı yol elemesiz geçer.
    kritik = [e for e in events if e["priority_lane"] == "kritik"]
    normal = [e for e in events if e["priority_lane"] != "kritik"][:12]
    if normal and storage.gemini_calls_today() + 1 <= cap:
        normal, elenen = brain.triage(normal)
        storage.log_gemini_call("triage")
        if elenen:
            print(f"  triage: {elenen} olay elendi, {len(normal)} kaldı")
    events = kritik + normal

    produced = 0
    per_cluster = {}  # aynı haber kümesinden en fazla 2 tez (kopya tez freni)
    for event in events:
        if produced >= MAX_THESES_PER_RUN:
            break
        if per_cluster.get(event["cluster_id"], 0) >= 2:
            continue
        used = storage.gemini_calls_today()
        if used + 2 > cap:
            print(f"Günlük Gemini tavanı doldu ({used}/{cap}) — kalan olaylar arşivleniyor (kuyruklanmaz).")
            break
        if storage.recent_thesis_exists(event["symbol"]):
            continue  # aynı sembolde 48 saat içinde tez var: mükerrer önleme
        try:
            print(f'\n[{event["symbol"]}] {event["title"][:80]}...')
            snapshot = prices.market_snapshot(event["symbol"], event["market"])
            draft = brain.draft_chain(event, snapshot)
            storage.log_gemini_call("taslak")
            if draft.get("tez_yok"):
                print(f'  -> taslak beyni reddetti: {draft.get("neden", "?")[:100]}')
                continue
            redteam = brain.red_team(event, draft, snapshot)
            storage.log_gemini_call("redteam")
            final, tier, status, neden = brain.merge(event, draft, redteam)
            # Referans fiyat + stop (2×ATR) — tez takibi bunlarla çalışır (plan bölüm 7)
            entry_ref = (snapshot or {}).get("price") or \
                prices.current_price(event["symbol"], event["market"])
            if entry_ref and status == "acik":
                atr = prices.atr14(event["symbol"], event["market"])
                if atr:
                    sign = 1 if draft["yon"] == "yukselis" else -1
                    inv = redteam.setdefault("gecersiz_kilma_kosulu", {})
                    inv["stop_fiyat"] = round(entry_ref - sign * 2 * atr, 2)
            thesis = storage.insert_thesis(event, draft, redteam, final, tier, status,
                                           entry_price_ref=entry_ref, note=neden)
            if status == "acik":
                produced += 1
                per_cluster[event["cluster_id"]] = per_cluster.get(event["cluster_id"], 0) + 1
            print(f"  -> güven={final}, katman={tier}, durum={status}"
                  + (f" ({neden})" if neden else ""))
            if status == "acik" and tier in ("kritik", "orta"):
                notifier.send(notifier.format_thesis(event, draft, redteam, final, tier))
                print("  -> Telegram bildirimi gönderildi")
        except Exception:
            print(f'  ! {event["symbol"]} işlenirken hata (pipeline devam ediyor):')
            traceback.print_exc(limit=2)

    print(f"\nBitti: {produced} açık tez. Bugünkü Gemini kullanımı: {storage.gemini_calls_today()}")


if __name__ == "__main__":
    missing = [k for k in ("GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN",
                           "TELEGRAM_CHAT_ID", "SUPABASE_URL", "SUPABASE_KEY")
               if not os.environ.get(k)]
    if missing:
        print("Eksik .env değişkenleri:", ", ".join(missing))
        print(".env.example dosyasını .env olarak kopyalayıp doldur.")
        sys.exit(1)
    run()
