"""Geriye dönük tez üretimi (plan bölüm 8).

Dashboard'dan "dışarıdan" pozisyon girilirken kullanıcı isterse talep
retro_thesis_queue'ya düşer. Tarama turunun başında (normal olaylardan ÖNCE,
kullanıcı talebi öncelikli) işlenir:

1. Sembolün açık tezi zaten varsa Gemini harcamadan ona bağlanır.
2. Yoksa toplanan haberlerden sembole en iyi uyan küme bulunur ve normal
   Aşama 2 akışı (taslak + red-team + merge) çalıştırılır; tez pozisyona
   geri yazılır. Referans fiyat = kullanıcının gerçek alış fiyatı.
3. Uygun haber yoksa talep bekliyor kalır (sonraki turlarda tekrar denenir);
   RETRY_DAYS gün içinde hiç olay çıkmazsa dürüstçe 'tez_bulunamadi' denir.
"""
from datetime import datetime, timedelta, timezone

from config import SYMBOLS
from src import brain, filter as f1, notifier, prices, storage

RETRY_DAYS = 3


def _best_cluster_for(symbol, clusters):
    """Sembole uyan en iyi küme: önce doğrudan eşleşme (1.0), sonra tema (0.4);
    eşitlikte çok kaynaklı küme tercih edilir."""
    best, best_key = None, (0.0, 0)
    for cluster in clusters:
        rep = cluster["rep"]
        text = (rep["title"] + " " + rep.get("summary", "")).lower()
        proximity = f1._match_symbols(text).get(symbol, 0.0)
        key = (proximity, len(cluster["members"]))
        if proximity > 0 and key > best_key:
            best, best_key = cluster, key
    return best


def _event_from_cluster(symbol, market, cluster):
    rep = cluster["rep"]
    text = rep["title"] + " " + rep.get("summary", "")
    return {
        "symbol": symbol,
        "market": market,
        "category": f1._guess_category(text),
        "relevance_score": 0.0,  # kullanıcı talebi — skor eşiği uygulanmaz
        "priority_lane": "normal_kuyruk",
        "title": rep["title"],
        "summary": rep.get("summary", ""),
        "url": rep.get("url"),
        "source": rep["source"],
        "source_count": len(cluster["members"]),
        "published_at": rep["published_at"],
    }


def _expired(req):
    created = datetime.fromisoformat(req["created_at"].replace("Z", "+00:00"))
    return datetime.now(timezone.utc) - created > timedelta(days=RETRY_DAYS)


def process_queue(clusters, cap):
    """Bekleyen geriye dönük tez taleplerini işle. Gemini tavanına saygılıdır."""
    requests = storage.pending_retro_requests()
    if not requests:
        return

    print(f"\nGeriye dönük tez kuyruğu: {len(requests)} talep")
    for req in requests:
        symbol = req["symbol"]
        pos = storage.get_position(req["position_id"]) if req.get("position_id") else None

        # 1) Açık tez zaten varsa Gemini harcamadan bağla
        existing = storage.open_thesis_for(symbol)
        if existing:
            if pos:
                storage.link_thesis_to_position(pos["id"], existing["id"])
            storage.update_retro(req["id"], "islendi", "mevcut açık teze bağlandı")
            notifier.send(f"🔗 {symbol}: pozisyonun mevcut açık teze bağlandı "
                          f"(güven: {existing['final_confidence']}). Takip otomatik sürecek.")
            print(f"  [{symbol}] mevcut açık teze bağlandı")
            continue

        # 2) İzleme evreni dışındaysa haber eşleşmesi imkansız — dürüst cevap
        if symbol not in SYMBOLS:
            storage.update_retro(req["id"], "tez_bulunamadi",
                                 "sembol izleme evreninde değil")
            notifier.send(f"ℹ️ {symbol}: geriye dönük tez kurulamadı — sembol "
                          f"izleme listemde yok (30 sembol). Pozisyon 'tez yok' "
                          f"olarak izlenir; fiyat takibi raporlarda sürer.")
            print(f"  [{symbol}] izleme evreni dışında")
            continue

        # 3) Uygun haber kümesi ara
        cluster = _best_cluster_for(symbol, clusters)
        if cluster is None:
            if _expired(req):
                storage.update_retro(req["id"], "tez_bulunamadi",
                                     f"{RETRY_DAYS} gün içinde uygun olay bulunamadı")
                notifier.send(f"ℹ️ {symbol}: geriye dönük tez kurulamadı — son "
                              f"{RETRY_DAYS} günün haberlerinde bu alımı destekleyecek "
                              f"bir olay bulamadım. Pozisyon 'tez yok' olarak izlenir.")
                print(f"  [{symbol}] süre doldu, olay yok")
            else:
                print(f"  [{symbol}] uygun olay yok, sonraki turda tekrar denenecek")
            continue

        # 4) Normal Aşama 2 akışı (kota kontrolü ile)
        used = storage.gemini_calls_today()
        if used + 2 > cap:
            print(f"  Gemini tavanı doldu ({used}/{cap}) — kuyruk bekliyor kalıyor")
            break
        market = SYMBOLS[symbol]["market"]
        event = _event_from_cluster(symbol, market, cluster)
        try:
            print(f'  [{symbol}] geriye dönük tez: {event["title"][:70]}...')
            draft = brain.draft_chain(event)
            storage.log_gemini_call("taslak")
            redteam = brain.red_team(event, draft)
            storage.log_gemini_call("redteam")
            final, tier, status = brain.merge(event, draft, redteam)
            # Referans = kullanıcının gerçek alış fiyatı; stop = 2×ATR (plan bölüm 7)
            entry_ref = float(pos["entry_price"]) if pos else \
                prices.current_price(symbol, market)
            if entry_ref:
                atr = prices.atr14(symbol, market)
                if atr:
                    sign = 1 if draft["yon"] == "yukselis" else -1
                    inv = redteam.setdefault("gecersiz_kilma_kosulu", {})
                    inv["stop_fiyat"] = round(entry_ref - sign * 2 * atr, 2)
            thesis = storage.insert_thesis(event, draft, redteam, final, tier, status,
                                           entry_price_ref=entry_ref)
            if pos:
                storage.link_thesis_to_position(pos["id"], thesis["id"])
            storage.update_retro(req["id"], "islendi", f"tez üretildi ({status})")
            if status == "acik":
                notifier.send(f"🧾 {symbol}: geriye dönük tez kuruldu (güven: {final}).\n"
                              f"Dayanak: {event['title'][:120]}\n"
                              f"Takip otomatik başladı — hedef/stop bildirimleri gelecek.")
            else:
                notifier.send(f"⚠️ {symbol}: geriye dönük tez denendi ama red-team "
                              f"gerekçeyi zayıf buldu (durum: {status}). Dürüst cevap: "
                              f"bu alımı destekleyen güçlü bir olay göremiyorum. "
                              f"Pozisyon yine de izlenecek.")
            print(f"  -> güven={final}, durum={status}")
        except Exception:
            import traceback
            print(f"  ! {symbol} geriye dönük tez hatası (kuyruk bekliyor kalıyor):")
            traceback.print_exc(limit=2)
