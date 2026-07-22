"""Supabase erişim katmanı: tezler, portföy, Gemini kota sayacı.

Kota günü Pasifik saatine (PT) göre hesaplanır — Gemini ücretsiz kota
PT gece yarısı sıfırlanır (plan bölüm 11).
"""
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from supabase import create_client

_client = None


def get_client():
    global _client
    if _client is None:
        _client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    return _client


def quota_date_pt():
    return datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()


def gemini_calls_today():
    rows = (get_client().table("gemini_usage_log")
            .select("call_count").eq("date", quota_date_pt()).execute().data)
    return sum(r["call_count"] for r in rows)


def log_gemini_call(call_type, count=1):
    get_client().table("gemini_usage_log").insert(
        {"date": quota_date_pt(), "call_type": call_type, "call_count": count}
    ).execute()


def ensure_symbols(symbols_config):
    """config.SYMBOLS'ü symbols tablosuna senkronla — sadece EKSİK olanlar
    yazılır (600 sembollük evreni her 30 dk'lık koşuda upsert etmemek için)."""
    client = get_client()
    existing = {r["symbol"] for r in
                client.table("symbols").select("symbol").execute().data}
    rows = [{"symbol": s, "name": i["name"], "market": i["market"],
             "sector": i.get("sector") or None, "theme_tags": i["themes"]}
            for s, i in symbols_config.items() if s not in existing]
    for start in range(0, len(rows), 200):
        client.table("symbols").upsert(rows[start:start + 200]).execute()
    if rows:
        print(f"  symbols tablosuna {len(rows)} yeni sembol eklendi")


def recent_thesis_exists(symbol, hours=48, kaynak=None):
    """Aynı sembol için son N saatte tez var mı? (mükerrer tez önleme, v1 basit hali)
    kaynak verilirse sadece o kaynaktan (örn. 'teknik') gelen tezlere bakar —
    faz 12: teknik radar kendi soğuma penceresini haber tezlerinden ayrı tutar."""
    from datetime import timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    q = get_client().table("theses").select("id").eq("symbol", symbol).gte("created_at", cutoff)
    if kaynak:
        q = q.eq("kaynak", kaynak)
    return len(q.execute().data) > 0


def insert_thesis(event, draft, redteam, final_confidence, tier, status,
                  entry_price_ref=None, note=None, kaynak="haber"):
    low, high = draft["buyukluk_araligi_pct"]
    row = {
        "resolution_note": note,
        "symbol": event["symbol"],
        "market": event["market"],
        "category": event["category"],
        "kaynak": kaynak,
        "draft_chain": draft,
        "redteam_output": redteam,
        "final_confidence": final_confidence,
        "notification_tier": tier,
        "direction": draft["yon"],
        "target_range_pct": f"[{low},{high}]",
        "horizon": f'{draft.get("ufuk_deger", "")} {draft["ufuk"]}'.strip(),
        "invalidation_condition": redteam.get("gecersiz_kilma_kosulu"),
        "entry_price_ref": entry_price_ref,
        "status": status,
    }
    return get_client().table("theses").insert(row).execute().data[0]


# --- tez takibi yardımcıları (plan bölüm 7) --------------------------------

def open_theses():
    return get_client().table("theses").select("*").eq("status", "acik").execute().data


def taslak_gozlem_theses():
    """Düşük güven ya da engel oranı yüzünden hiç açılmamış (status='taslak',
    tier='gozlem') tezler — önceden asla kontrol edilmiyor, sonsuza kadar
    donuk kalıyordu (karneye giremiyor, gerçekte doğru çıksa bile görünmüyordu).
    Artık sessizce (bildirimsiz) kontrol edilip bir sonuca bağlanıyorlar."""
    return (get_client().table("theses").select("*")
            .eq("status", "taslak").eq("notification_tier", "gozlem").execute().data)


def update_thesis(thesis_id, **fields):
    get_client().table("theses").update(fields).eq("id", thesis_id).execute()


def insert_thesis_check(thesis_id, price, snapshot, result):
    get_client().table("thesis_checks").insert({
        "thesis_id": thesis_id, "price_at_check": price,
        "signal_snapshot": snapshot, "result": result,
    }).execute()


def log_mesaj(tur, icerik, basarili, telegram_message_id=None, hata_metni=None):
    """Faz 12 sonrası: notifier.send() üzerinden giden HER mesaj (başarılı ya
    da başarısız) buraya yazılır — dashboard'daki mesajlaşma merkezinin
    (/bildirimler) veri kaynağı. Eskiden sadece tez yaşam-döngüsü bildirimleri
    (alerts tablosu) loglanıyordu, yeni tez/rapor/teknik fırsat mesajları hiç
    kayıtlı değildi."""
    get_client().table("mesaj_log").insert({
        "tur": tur, "icerik": icerik, "basarili": basarili,
        "telegram_message_id": str(telegram_message_id) if telegram_message_id else None,
        "hata_metni": hata_metni,
    }).execute()


def log_error(kaynak, mesaj, detay=None, seviye="normal"):
    """Merkezi hata kaydı — dashboard'daki /hatalar sayfasının veri kaynağı.
    Faz 12 sonrası Gemini kesintisi 12+ saat fark edilmeden sürdüğü için
    eklendi (mevcut try/except'ler hatayı yutup pipeline'ı sürdürüyordu ama
    hiçbir yerde görünmüyordu)."""
    try:
        get_client().table("sistem_hatalari").insert({
            "kaynak": kaynak, "mesaj": mesaj[:500] if mesaj else mesaj,
            "detay": detay[:2000] if detay else None, "seviye": seviye,
        }).execute()
    except Exception:
        pass  # hata kaydı başarısız oldu diye ana akış durmasın


def alert_exists(alert_type, thesis_id):
    """Aynı tez için aynı tip bildirim daha önce gitti mi? (tekrar önleme)"""
    rows = (get_client().table("alerts").select("id")
            .eq("type", alert_type).eq("thesis_id", thesis_id).execute().data)
    return len(rows) > 0


def log_alert(alert_type, thesis_id, message_id, summary):
    get_client().table("alerts").insert({
        "type": alert_type, "thesis_id": thesis_id,
        "telegram_message_id": str(message_id), "content_summary": summary[:300],
    }).execute()


def insert_kurtarma(thesis_id, signals, verdict, oran):
    get_client().table("kurtarma_degerlendirmeleri").insert({
        "thesis_id": thesis_id, "triggered_signals": signals,
        "ai_verdict": verdict, "cikis_orani": oran,
    }).execute()


def kurtarma_exists_recent(thesis_id, days=7):
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = (get_client().table("kurtarma_degerlendirmeleri").select("id")
            .eq("thesis_id", thesis_id).gte("created_at", cutoff).execute().data)
    return len(rows) > 0


def insert_izleme(symbol, market, yon, mekanizma, guven, kaynak_baslik, kaynak_url):
    return get_client().table("ikinci_derece_izleme").insert({
        "symbol": symbol, "market": market, "yon": yon, "mekanizma": mekanizma,
        "guven": guven, "kaynak_baslik": kaynak_baslik, "kaynak_url": kaynak_url,
    }).execute().data[0]


def pending_izleme():
    return (get_client().table("ikinci_derece_izleme").select("*")
            .eq("status", "bekliyor").execute().data)


def close_izleme(izleme_id, status):
    get_client().table("ikinci_derece_izleme").update({
        "status": status, "resolved_at": "now()",
    }).eq("id", izleme_id).execute()


def get_settings():
    """user_settings satırı (engel oranı vb.). Kolon henüz yoksa boş döner."""
    try:
        rows = get_client().table("user_settings").select("*").eq("id", 1).execute().data
        return rows[0] if rows else {}
    except Exception:
        return {}


# --- geriye dönük tez kuyruğu (plan bölüm 8, dashboard köprüsü) -------------

def pending_retro_requests():
    return (get_client().table("retro_thesis_queue").select("*")
            .eq("status", "bekliyor").order("created_at").execute().data)


def update_retro(req_id, status, note=None):
    get_client().table("retro_thesis_queue").update({
        "status": status, "note": note, "processed_at": "now()",
    }).eq("id", req_id).execute()


def get_position(position_id):
    rows = (get_client().table("portfolio").select("*")
            .eq("id", position_id).execute().data)
    return rows[0] if rows else None


def link_thesis_to_position(position_id, thesis_id):
    get_client().table("portfolio").update({"thesis_id": thesis_id}) \
        .eq("id", position_id).execute()


def open_thesis_for(symbol):
    """Sembolün en yeni açık tezi (geriye dönük talepte önce buna bağlanır)."""
    rows = (get_client().table("theses").select("*")
            .eq("symbol", symbol).eq("status", "acik")
            .order("created_at", desc=True).limit(1).execute().data)
    return rows[0] if rows else None


def open_portfolio_symbols():
    rows = (get_client().table("portfolio").select("symbol")
            .eq("status", "acik").execute().data)
    return frozenset(r["symbol"] for r in rows)


def add_position(symbol, market, quantity, entry_price, entry_date,
                 portfolio_type, thesis_id=None):
    row = {
        "symbol": symbol, "market": market, "quantity": quantity,
        "entry_price": entry_price, "entry_date": entry_date,
        "source": "sistem_tezi" if thesis_id else "disaridan",
        "portfolio_type": portfolio_type, "thesis_id": thesis_id,
    }
    return get_client().table("portfolio").insert(row).execute().data[0]


def close_position(symbol, quantity=None, reason=None, close_price=None):
    """Pozisyonu kapat; bağlı tez varsa otomatik kullanici_satti yap (plan: entegrasyon #3).
    close_price verilmezse gerçekleşen K/Z hesaplanamaz (metrics %0 varsayar)."""
    client = get_client()
    rows = (client.table("portfolio").select("*")
            .eq("symbol", symbol).eq("status", "acik").execute().data)
    if not rows:
        return None
    pos = rows[0]
    full_close = quantity is None or quantity >= pos["quantity"]
    if full_close:
        client.table("portfolio").update({
            "status": "kapali", "closed_at": "now()",
            "closed_quantity": pos["quantity"], "close_reason": reason,
            "close_price": close_price,
        }).eq("id", pos["id"]).execute()
        if pos.get("thesis_id"):
            client.table("theses").update({
                "status": "kullanici_satti", "resolved_at": "now()",
                "resolution_note": reason or "kullanıcı manuel kapattı",
            }).eq("id", pos["thesis_id"]).eq("status", "acik").execute()
    else:
        client.table("portfolio").update({
            "quantity": pos["quantity"] - quantity,
            "closed_quantity": (pos.get("closed_quantity") or 0) + quantity,
            "close_price": close_price,  # son kısmi satış fiyatı (yaklaşıklık)
        }).eq("id", pos["id"]).execute()
    return pos


def list_positions(portfolio_type=None):
    q = get_client().table("portfolio").select("*").eq("status", "acik")
    if portfolio_type:
        q = q.eq("portfolio_type", portfolio_type)
    return q.execute().data
