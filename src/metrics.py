"""Getiri metrikleri (plan bölüm 7.4) — kullanıcının asıl hedefini ölçer:
"sistemi bir yıl takip etseydim portföyüm ne kazandırırdı?"

Üç kapsam (scope):
  gercek / deneme — portföy bazlı: toplam getiri, XIRR, benchmark karşılaştırması
  tezler          — tez bazlı: isabet oranı, ort. kazanç/kayıp, expectancy

Her rapor turunda hesaplanıp portfolio_metrics'e anlık görüntü yazılır;
dashboard son kaydı okur. Az veriyle dürüst davranır: hesaplanamayan metrik
None kalır ve 'notlar' alanında nedeni yazar.
"""
from datetime import date, datetime, timezone

import yfinance as yf

from src import prices, storage

MIN_XIRR_DAYS = 7      # bundan kısa sürede yıllıklandırma yanıltıcı olur
MIN_THESES = 5         # bundan az çözülmüş tezle expectancy anlamsız
BENCH = {"BIST100": "XU100.IS", "S&P500": "^GSPC"}


def _xirr(cashflows):
    """Düzensiz nakit akışlarından yıllık getiri. cashflows: [(date, tutar)].
    Negatif = yatırılan para, pozitif = geri dönen/mevcut değer. Bisection —
    scipy bağımlılığı olmadan sağlam kök bulma."""
    if len(cashflows) < 2:
        return None
    t0 = min(d for d, _ in cashflows)

    def npv(rate):
        return sum(cf / (1 + rate) ** ((d - t0).days / 365.0) for d, cf in cashflows)

    lo, hi = -0.999, 10.0
    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        f = npv(mid)
        if abs(f) < 1e-9:
            break
        if f * f_lo < 0:
            hi = mid
        else:
            lo, f_lo = mid, f
    return round(mid * 100, 2)


def _benchmark_return(ticker, start):
    """start'tan bugüne buy-and-hold getirisi (%)."""
    try:
        df = yf.download(ticker, start=start.isoformat(), progress=False,
                         auto_adjust=True)
        closes = df["Close"]
        if hasattr(closes, "columns"):  # tek sembolde de MultiIndex dönebiliyor
            closes = closes.iloc[:, 0]
        closes = closes.dropna()
        if len(closes) < 2:
            return None
        return round(float(closes.iloc[-1] / closes.iloc[0] - 1) * 100, 2)
    except Exception:
        return None


def portfolio_scope(ptype):
    """Bir portföy türünün (gercek/deneme) getiri metrikleri."""
    rows = (storage.get_client().table("portfolio").select("*")
            .eq("portfolio_type", ptype).order("entry_date").execute().data)
    if not rows:
        return None
    notlar = []
    flows = []            # XIRR nakit akışları
    yatirilan = 0.0
    acik_deger = 0.0
    gerceklesen = 0.0     # kapalı pozisyonlardan dönen para
    today = datetime.now(timezone.utc).date()

    for p in rows:
        ep = float(p["entry_price"])
        entry_d = date.fromisoformat(p["entry_date"])
        if p["status"] == "acik":
            qty = float(p["quantity"])
            cur = prices.current_price(p["symbol"], p["market"])
            if cur is None:
                cur = ep
                notlar.append(f'{p["symbol"]}: güncel fiyat alınamadı, alış fiyatı varsayıldı')
            yatirilan += qty * ep
            acik_deger += qty * cur
            flows.append((entry_d, -qty * ep))
            # kısmen kapatılmış açık pozisyonun kapanan dilimi de sayılmalı
            cq = float(p.get("closed_quantity") or 0)
            if cq:
                yatirilan += cq * ep
                flows.append((entry_d, -cq * ep))
                cp = p.get("close_price")
                if cp is None:
                    gerceklesen += cq * ep
                    flows.append((today, cq * ep))
                    notlar.append(f'{p["symbol"]}: kısmi satış fiyatı kayıtlı değil, %0 varsayıldı')
                else:
                    gerceklesen += cq * float(cp)
                    flows.append((today, cq * float(cp)))
        else:  # kapalı
            cq = float(p.get("closed_quantity") or p["quantity"])
            closed_d = date.fromisoformat(p["closed_at"][:10]) if p.get("closed_at") else today
            yatirilan += cq * ep
            flows.append((entry_d, -cq * ep))
            cp = p.get("close_price")
            if cp is None:
                cp = ep
                notlar.append(f'{p["symbol"]}: satış fiyatı kayıtlı değil, %0 varsayıldı')
            gerceklesen += cq * float(cp)
            flows.append((closed_d, cq * float(cp)))

    if not yatirilan:
        return None
    if acik_deger:
        flows.append((today, acik_deger))

    toplam_getiri = round((acik_deger + gerceklesen - yatirilan) / yatirilan * 100, 2)

    baslangic = min(d for d, _ in flows)
    gun = (today - baslangic).days
    xirr = None
    if gun >= MIN_XIRR_DAYS:
        xirr = _xirr(flows)
    else:
        notlar.append(f"süre çok kısa ({gun} gün) — XIRR {MIN_XIRR_DAYS}. günden sonra hesaplanır")

    benchmark = {ad: _benchmark_return(tkr, baslangic) for ad, tkr in BENCH.items()}
    if gun < 2:
        notlar.append("benchmark için de süre çok kısa — birkaç gün sonra anlamlı olur")

    return {
        "yatirilan": round(yatirilan, 2),
        "acik_deger": round(acik_deger, 2),
        "gerceklesen": round(gerceklesen, 2),
        "toplam_getiri_pct": toplam_getiri,
        "xirr_pct": xirr,
        "benchmark_pct": benchmark,
        "baslangic": baslangic.isoformat(),
        "gun": gun,
        "acik_pozisyon": sum(1 for p in rows if p["status"] == "acik"),
        "kapali_pozisyon": sum(1 for p in rows if p["status"] != "acik"),
        "notlar": notlar,
    }


def thesis_scope():
    """Çözülmüş tezlerden isabet + expectancy (plan 7.4). Deneme portföyünden
    bağımsızdır — sistemin öğrenme/başarı ölçüsü tezlerin kendisidir."""
    resolved = (storage.get_client().table("theses")
                .select("id,symbol,direction,status,entry_price_ref")
                .in_("status", ["hedefe_ulasti", "tez_bozuldu", "suresi_doldu"])
                .not_.is_("entry_price_ref", "null").execute().data)
    gains = []
    for t in resolved:
        checks = (storage.get_client().table("thesis_checks")
                  .select("price_at_check").eq("thesis_id", t["id"])
                  .order("checked_at", desc=True).limit(1).execute().data)
        if not checks or not checks[0]["price_at_check"]:
            continue
        ref = float(t["entry_price_ref"])
        son = float(checks[0]["price_at_check"])
        sign = 1 if t["direction"] == "yukselis" else -1
        gains.append({"symbol": t["symbol"], "status": t["status"],
                      "pct": round((son - ref) / ref * 100 * sign, 2)})

    n = len(gains)
    out = {"cozulmus_tez": n, "notlar": []}
    if n < MIN_THESES:
        out["notlar"].append(f"yetersiz veri ({n} çözülmüş tez) — "
                             f"expectancy ≥{MIN_THESES} tezle hesaplanır")
        return out

    kazananlar = [g["pct"] for g in gains if g["pct"] > 0]
    kaybedenler = [abs(g["pct"]) for g in gains if g["pct"] <= 0]
    isabet = len(kazananlar) / n
    ort_kazanc = sum(kazananlar) / len(kazananlar) if kazananlar else 0.0
    ort_kayip = sum(kaybedenler) / len(kaybedenler) if kaybedenler else 0.0
    out.update({
        "isabet_orani": round(isabet, 3),
        "ort_kazanc_pct": round(ort_kazanc, 2),
        "ort_kayip_pct": round(ort_kayip, 2),
        "expectancy_pct": round(isabet * ort_kazanc - (1 - isabet) * ort_kayip, 2),
    })
    return out


def compute_and_store():
    """Tüm kapsamları hesapla ve portfolio_metrics'e yaz. Rapor turundan çağrılır."""
    client = storage.get_client()
    results = {}
    for scope, fn in (("gercek", lambda: portfolio_scope("gercek")),
                      ("deneme", lambda: portfolio_scope("deneme")),
                      ("tezler", thesis_scope)):
        m = fn()
        if m is not None:
            client.table("portfolio_metrics").insert(
                {"scope": scope, "metrics": m}).execute()
            results[scope] = m
    return results
