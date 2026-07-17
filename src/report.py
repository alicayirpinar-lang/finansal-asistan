"""Günlük rapor (plan bölüm 9): pazar başına, bölüm başına ayrı Telegram mesajı.

Bölümler: özet -> orta öncelikli yeni tezler -> gözlem (teknik) -> portföy.
Boş bölüm gönderilmez. Teknik sinyaller rapor anında hesaplanır ve
technical_signals'a yazılır (tüm semboller; gözlem filtresi sadece görünümde).
"""
from datetime import datetime, timedelta, timezone

from src import notifier, prices, signals, storage

_GUVEN = {"dusuk": "düşük", "orta": "orta", "yuksek": "yüksek"}
_TRIGGER_TXT = {
    "hacim_anomalisi": "hacim anomalisi", "rsi_asiri_satim": "RSI aşırı satım",
    "rsi_asiri_alim": "RSI aşırı alım", "ma20_kesisim": "MA20 kesişimi",
    "52h_zirve_yakini": "52h zirvesine yakın", "52h_dip_yakini": "52h dibine yakın",
}


def _recent_theses(market, hours=24):
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    return (storage.get_client().table("theses")
            .select("symbol,direction,final_confidence,notification_tier,horizon,target_range_pct,status")
            .eq("market", market).gte("created_at", cutoff)
            .neq("status", "iptal_edildi").execute().data)


def _thesis_status_map(ids):
    if not ids:
        return {}
    rows = (storage.get_client().table("theses").select("id,status")
            .in_("id", ids).execute().data)
    return {r["id"]: r["status"] for r in rows}


def build_and_send(market):
    now_str = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    sections_sent = []

    # Teknik sinyaller: hesapla + tümünü DB'ye yaz
    signal_rows = signals.compute_signals(market)
    if signal_rows:
        db_rows = [{k: v for k, v in r.items() if not k.startswith("_")} for r in signal_rows]
        storage.get_client().table("technical_signals").insert(db_rows).execute()
    gozlem = sorted([r for r in signal_rows if r["gozlem_skoru"]],
                    key=lambda r: -r["gozlem_skoru"])[:10]

    theses = _recent_theses(market)
    orta = [t for t in theses if t["notification_tier"] == "orta"]

    positions = [p for p in storage.list_positions() if p["market"] == market]

    # 1) Özet
    notifier.send(f"📋 Günlük rapor — {market} · {now_str}\n"
                  f"Son 24 saat: {len(theses)} yeni tez ({len(orta)} orta öncelikli)\n"
                  f"Gözlem sinyali: {len(gozlem)} sembol · Açık pozisyon: {len(positions)}")
    sections_sent.append("ozet")

    # 2) Orta öncelikli tezler (kritikler zaten anlık gitti)
    if orta:
        lines = ["ℹ️ Orta öncelikli yeni tezler:"]
        for t in orta:
            yon = "yükseliş" if t["direction"] == "yukselis" else "düşüş"
            lines.append(f'• {t["symbol"]} — {yon}, güven: {_GUVEN[t["final_confidence"]]}, '
                         f'hedef {t["target_range_pct"]}, ufuk {t["horizon"]}')
        notifier.send("\n".join(lines))
        sections_sent.append("orta_tezler")

    # 3) Gözlem — nötr çerçeveleme şart (plan: sebep içermez, tezlerle aynı dilde sunulmaz)
    if gozlem:
        lines = ["👁 Gözlemlenen anormallikler (istatistiksel — sebebi belirtilmemiştir):"]
        for g in gozlem:
            yon = "↑" if g["_direction"] == "yukselis" else "↓"
            lines.append(f'• {g["symbol"]} {yon}  [{", ".join(_TRIGGER_TXT.get(t, t) for t in g["_triggers"])}]'
                         f'  skor {g["gozlem_skoru"]:.1f}')
        lines.append("Bunlar tez değildir; sadece sıra dışı hareket bildirimidir.")
        notifier.send("\n".join(lines))
        sections_sent.append("gozlem")

    # 4) Portföy (gerçek/deneme ayrı — asla aynı toplamda gösterilmez)
    if positions:
        status_map = _thesis_status_map([p["thesis_id"] for p in positions if p.get("thesis_id")])
        lines = [f"💼 Portföyün ({market}):"]
        for ptype in ("gercek", "deneme"):
            group = [p for p in positions if p["portfolio_type"] == ptype]
            if not group:
                continue
            lines.append(f'\n[{"GERÇEK" if ptype == "gercek" else "DENEME"}]')
            for p in group:
                price = prices.current_price(p["symbol"], market)
                if price:
                    pnl = (price - float(p["entry_price"])) / float(p["entry_price"]) * 100
                    pnl_txt = f"%{pnl:+.1f}"
                else:
                    pnl_txt = "fiyat alınamadı"
                tez_txt = f' · tez: {status_map.get(p["thesis_id"], "?")}' if p.get("thesis_id") else " · tez yok"
                lines.append(f'• {p["symbol"]}: {p["quantity"]:g} adet @ {p["entry_price"]} → {pnl_txt}{tez_txt}')
        notifier.send("\n".join(lines))
        sections_sent.append("portfoy")

    storage.get_client().table("daily_reports").insert({
        "market": market, "report_date": datetime.now(timezone.utc).date().isoformat(),
        "sections_sent": sections_sent,
    }).execute()
    return sections_sent
