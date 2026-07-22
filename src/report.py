"""Günlük rapor (plan bölüm 9): pazar başına, bölüm başına ayrı Telegram mesajı.

Bölümler: özet -> orta öncelikli yeni tezler -> gözlem (teknik) -> portföy.
Boş bölüm gönderilmez. Teknik sinyaller rapor anında hesaplanır ve
technical_signals'a yazılır (tüm semboller; gözlem filtresi sadece görünümde).
"""
from datetime import datetime, timedelta, timezone

from config import TEKNIK_RADAR_GUNLUK_CAP, TEKNIK_RADAR_SOGUMA_GUN
from src import analytics, metrics, notifier, prices, signals, storage

_GUVEN = {"dusuk": "düşük", "orta": "orta", "yuksek": "yüksek"}
_TRIGGER_TXT = {
    "hacim_anomalisi": "hacim anomalisi", "rsi_asiri_satim": "RSI aşırı satım",
    "rsi_asiri_alim": "RSI aşırı alım", "ma20_kesisim": "MA20 kesişimi",
    "52h_zirve_yakini": "52h zirvesine yakın", "52h_dip_yakini": "52h dibine yakın",
}


def _recent_theses(market, hours=24):
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    return (storage.get_client().table("theses")
            .select("symbol,direction,final_confidence,notification_tier,horizon,target_range_pct,status,kaynak")
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
        for start in range(0, len(db_rows), 200):  # 600 sembol tek insert'e sığmasın
            chunk = db_rows[start:start + 200]
            try:
                storage.get_client().table("technical_signals").insert(chunk).execute()
            except Exception:
                # 'analiz' kolonu henüz yoksa (migration 004 bekliyor) kolonsuz yaz
                for r in chunk:
                    r.pop("analiz", None)
                storage.get_client().table("technical_signals").insert(chunk).execute()
    # Faz 12 A — teknik radar: kanıtlı kurulumlardan Gemini'siz takip edilen
    # pozisyon üretir (Gemini kotası çökse bile çalışan tek fırsat kaynağı).
    # Giriş/stop/hedef kod ile (AI hikayesi yok); ayrı "📈 TEKNİK FIRSAT" mesajı gider.
    rejim_bilgi = analytics.rejim(market)
    acilan_semboller = set()
    try:
        for aday in signals.teknik_pozisyon_adaylari(signal_rows, market, rejim_bilgi)[:TEKNIK_RADAR_GUNLUK_CAP]:
            if storage.recent_thesis_exists(aday["symbol"], hours=24 * TEKNIK_RADAR_SOGUMA_GUN, kaynak="teknik"):
                continue  # soğuma penceresi (~10 gün): aynı sembolde tekrar açma
            s = aday["kurulum"]
            draft = {
                "yon": "yukselis",
                "buyukluk_araligi_pct": [aday["hedef_dusuk"], aday["hedef_yuksek"]],
                "ufuk": "ay", "ufuk_deger": 1,
                "zincir": [{
                    "adim_no": 1,
                    "mekanizma": f'Teknik kurulum: {s["ad"]} (backtest kanıtlı, AI yorumu yok) — '
                                 + "; ".join(s["kosullar"]),
                    "guven": "orta", "dayanak": f'skor {s["skor"]}, örneklem-dışı backtest (bkz. tools/backtest_kurulum.py)',
                }],
                "teknik_gorunum": {
                    "katalizor": "teknik", "buyuk_firsat": False,
                    "rejim": rejim_bilgi.get("rejim"), "kurulumlar": [s], "tepki": None, "engel": "",
                },
            }
            redteam = {"gecersiz_kilma_kosulu": {
                "kosul": f'kapanış fiyatı {aday["stop"]} altına düşerse (2×ATR stop)',
                "izleme_yontemi": "fiyat_seviyesi", "stop_fiyat": aday["stop"],
            }}
            event = {"symbol": aday["symbol"], "market": market, "category": "teknik"}
            storage.insert_thesis(event, draft, redteam, "orta", "orta", "acik",
                                  entry_price_ref=aday["entry"],
                                  note="teknik radar (faz 12, Gemini kullanılmadı)",
                                  kaynak="teknik")
            acilan_semboller.add(aday["symbol"])
            notifier.send(notifier.format_teknik_firsat(aday, market, rejim_bilgi), tur="teknik_firsat")
        if acilan_semboller:
            sections_sent.append("teknik_pozisyon")
    except Exception:
        # 'kaynak' kolonu henüz yoksa (migration 005 bekliyor) ya da başka bir
        # hata olursa rapor devam etsin (metrikler bölümüyle aynı dayanıklılık ilkesi).
        import traceback
        print("Teknik radar hatası (rapor devam ediyor):")
        traceback.print_exc(limit=2)
        storage.log_error("report.py:teknik_radar", "Teknik radar hatası", traceback.format_exc())

    gozlem = sorted([r for r in signal_rows if r["gozlem_skoru"]],
                    key=lambda r: -r["gozlem_skoru"])[:10]

    theses = _recent_theses(market)
    orta = [t for t in theses if t["notification_tier"] == "orta" and t.get("kaynak") != "teknik"]

    positions = [p for p in storage.list_positions() if p["market"] == market]

    # 1) Özet
    notifier.send(f"📋 Günlük rapor — {market} · {now_str}\n"
                  f"Son 24 saat: {len(theses)} yeni tez ({len(orta)} orta öncelikli)\n"
                  f"Gözlem sinyali: {len(gozlem)} sembol · Açık pozisyon: {len(positions)}",
                  tur="rapor_ozet")
    sections_sent.append("ozet")

    # 2) Orta öncelikli tezler (kritikler zaten anlık gitti)
    if orta:
        lines = ["ℹ️ Orta öncelikli yeni tezler:"]
        for t in orta:
            yon = "yükseliş" if t["direction"] == "yukselis" else "düşüş"
            lines.append(f'• {t["symbol"]} — {yon}, güven: {_GUVEN[t["final_confidence"]]}, '
                         f'hedef {t["target_range_pct"]}, ufuk {t["horizon"]}')
        notifier.send("\n".join(lines), tur="rapor_orta_tezler")
        sections_sent.append("orta_tezler")

    # 2.5) Büyük hareket kurulumları (analitik motor, faz 11) — haber beklemeden
    # "yay gerilmiş" hisseleri gösterir; nötr dil, tez değildir.
    kurulumlu = [r for r in signal_rows
                 if r["symbol"] not in acilan_semboller
                 and any(s.get("kanitli") and s["skor"] >= 70
                        for s in r.get("_setups", []))][:8]
    if kurulumlu:
        lines = ["🎯 Büyük hareket kurulumları (backtest kanıtlı — haber katalizörü henüz yok):"]
        for r in kurulumlu:
            for s in r["_setups"]:
                if s.get("kanitli") and s["skor"] >= 70:
                    lines.append(f'• {r["symbol"]}: {s["ad"]} (skor {s["skor"]}) — '
                                 + "; ".join(s["kosullar"][:3]))
        lines.append("Bunlar tez değildir; katalizör çıkarsa sistem önceliklendirir.")
        notifier.send("\n".join(lines), tur="rapor_kurulumlar")
        sections_sent.append("kurulumlar")

    # 3) Gözlem — nötr çerçeveleme şart (plan: sebep içermez, tezlerle aynı dilde sunulmaz)
    if gozlem:
        lines = ["👁 Gözlemlenen anormallikler (istatistiksel — sebebi belirtilmemiştir):"]
        for g in gozlem:
            yon = "↑" if g["_direction"] == "yukselis" else "↓"
            lines.append(f'• {g["symbol"]} {yon}  [{", ".join(_TRIGGER_TXT.get(t, t) for t in g["_triggers"])}]'
                         f'  skor {g["gozlem_skoru"]:.1f}')
        lines.append("Bunlar tez değildir; sadece sıra dışı hareket bildirimidir.")
        notifier.send("\n".join(lines), tur="rapor_gozlem")
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
        notifier.send("\n".join(lines), tur="rapor_portfoy")
        sections_sent.append("portfoy")

    # Getiri metrikleri anlık görüntüsü (plan 7.4) — dashboard /getiri buradan okur.
    # Hata raporu düşürmesin: metrik hesabı çökse de rapor gönderilmiş sayılır.
    try:
        metrics.compute_and_store()
        sections_sent.append("metrikler")
    except Exception:
        import traceback
        print("Getiri metrikleri hesaplanamadı (rapor etkilenmez):")
        traceback.print_exc(limit=2)
        storage.log_error("report.py:metrikler", "Getiri metrikleri hesaplanamadı", traceback.format_exc())

    storage.get_client().table("daily_reports").insert({
        "market": market, "report_date": datetime.now(timezone.utc).date().isoformat(),
        "sections_sent": sections_sent,
    }).execute()
    return sections_sent
