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
    """config.SYMBOLS sözlüğünü symbols tablosuna senkronla (upsert)."""
    rows = [{"symbol": s, "name": i["name"], "market": i["market"],
             "theme_tags": i["themes"]} for s, i in symbols_config.items()]
    get_client().table("symbols").upsert(rows).execute()


def recent_thesis_exists(symbol, hours=48):
    """Aynı sembol için son N saatte tez var mı? (mükerrer tez önleme, v1 basit hali)"""
    from datetime import timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    rows = (get_client().table("theses").select("id")
            .eq("symbol", symbol).gte("created_at", cutoff).execute().data)
    return len(rows) > 0


def insert_thesis(event, draft, redteam, final_confidence, tier, status,
                  entry_price_ref=None):
    low, high = draft["buyukluk_araligi_pct"]
    row = {
        "symbol": event["symbol"],
        "market": event["market"],
        "category": event["category"],
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


def update_thesis(thesis_id, **fields):
    get_client().table("theses").update(fields).eq("id", thesis_id).execute()


def insert_thesis_check(thesis_id, price, snapshot, result):
    get_client().table("thesis_checks").insert({
        "thesis_id": thesis_id, "price_at_check": price,
        "signal_snapshot": snapshot, "result": result,
    }).execute()


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


def close_position(symbol, quantity=None, reason=None):
    """Pozisyonu kapat; bağlı tez varsa otomatik kullanici_satti yap (plan: entegrasyon #3)."""
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
        }).eq("id", pos["id"]).execute()
    return pos


def list_positions(portfolio_type=None):
    q = get_client().table("portfolio").select("*").eq("status", "acik")
    if portfolio_type:
        q = q.eq("portfolio_type", portfolio_type)
    return q.execute().data
