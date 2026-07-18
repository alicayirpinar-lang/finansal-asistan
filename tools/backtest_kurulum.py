"""Kurulum kurallarının kanıt testi (faz 11) — 10 yıl, örneklem içi/dışı.

Kullanım: python tools/backtest_kurulum.py [--hizli]
  --hizli: pazar başına 40 sembollük örneklemle (ilk doğrulama için)

Metodoloji (literatür dersleri):
- Eşikler analytics.py'de DONMUŞ — bu araç sadece RAPORLAR, ayar yapmaz.
  Sonuca bakıp eşik oynamak p-hacking'dir (Bailey et al.: canlı performans
  backtest'ten medyan %73 kötü; karmaşıklık farkı büyütür).
- Örneklem içi: 2016-2022 | Örneklem dışı: 2023-bugün. Kural ancak İKİSİNDE
  de taban çizgisini geçerse "kanıtlı" sayılır.
- Üst üste binen sinyaller ayıklanır (10 gün içinde tekrar = aynı sinyal).
- Bakış açısı ileriye dönük: sinyal günü kapanışından 20 işlem günü sonrasına.
"""
import json
import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import SYMBOLS                      # noqa: E402
from src import analytics as A                  # noqa: E402
from src.prices import yf_ticker                # noqa: E402

SPLIT = "2023-01-01"
FWD = 20          # ileri bakış: 20 işlem günü
DEDUP_GUN = 10    # aynı sinyalin tekrarı sayılmaz penceresi
OUT = Path(__file__).resolve().parent.parent / "data" / "backtest_sonuclari.json"


def _series_setups(df, idx_close):
    """Kurulum koşullarını SERİ olarak hesapla (analytics eşikleriyle aynı)."""
    c, v, h, l = df["Close"], df["Volume"], df["High"], df["Low"]
    ma20, ma50, ma200 = c.rolling(20).mean(), c.rolling(50).mean(), c.rolling(200).mean()

    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = 100 - 100 / (1 + up / dn.replace(0, float("nan")))

    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()

    up_dm, dn_dm = h.diff(), -l.diff()
    plus = (((up_dm > dn_dm) & (up_dm > 0)) * up_dm).ewm(alpha=1 / 14, adjust=False).mean()
    minus = (((dn_dm > up_dm) & (dn_dm > 0)) * dn_dm).ewm(alpha=1 / 14, adjust=False).mean()
    atr_nz = atr.replace(0, float("nan"))
    pdi, mdi = 100 * plus / atr_nz, 100 * minus / atr_nz
    adx = (100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, float("nan"))) \
        .ewm(alpha=1 / 14, adjust=False).mean()

    bbw = (4 * c.rolling(20).std()) / ma20.replace(0, float("nan"))
    bbw_pctl = bbw.rolling(252).rank(pct=True) * 100

    vol_z = (v - v.rolling(20).mean()) / v.rolling(20).std().replace(0, float("nan"))
    hi52 = c.rolling(252).max()
    dir120 = c.rolling(120).max()
    obv = (v * d.apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))).cumsum()

    rs = None
    if idx_close is not None:
        # saat dilimi uyuşmazlığı reindex'i boşaltır -> ikisini de naive yap
        ic = idx_close.copy()
        if getattr(ic.index, "tz", None) is not None:
            ic.index = ic.index.tz_localize(None)
        cc = c.copy()
        if getattr(cc.index, "tz", None) is not None:
            cc.index = cc.index.tz_localize(None)
        aligned = ic.reindex(cc.index).ffill()
        rs = (cc / cc.shift(66) - 1) - (aligned / aligned.shift(66) - 1)
        rs.index = c.index

    setups = {
        "sikisma_kirilim_adayi": (bbw_pctl <= A.SIKISMA_PCTL)
            & ((dir120 - c) / c * 100 <= A.KIRILIM_YAKIN_PCT)
            & (obv > obv.shift(20)),
        "taban_kirilimi": ((hi52 - c) / hi52 * 100 <= 2.0) & (vol_z >= A.HACIM_ONAY_Z),
        "momentum_devam": (c > ma50) & (ma50 > ma200) & (adx >= A.ADX_TREND_ESIK)
            & ((c - ma20).abs() <= atr)
            & ((rs > 0) if rs is not None else True),
        "asiri_gerilme": ((c - ma20).abs() >= A.GERILME_ATR * atr) | (rsi >= 80),
    }
    return setups


def _dedup(mask):
    """Üst üste binen sinyalleri ayıkla: DEDUP_GUN içinde tekrar sayılmaz."""
    out, last = [], -10**9
    for i, val in enumerate(mask.values):
        if val and i - last >= DEDUP_GUN:
            out.append(i)
            last = i
    return out


def run(hizli=False):
    sonuc = {}
    for market in ("BIST", "US"):
        syms = [s for s, i in SYMBOLS.items() if i["market"] == market]
        if hizli:
            syms = syms[:40]
        idx = yf.Ticker(A.ENDEKS[market]).history(period="10y")["Close"]
        kayitlar = {ad: {"in": [], "out": []} for ad in
                    ("sikisma_kirilim_adayi", "taban_kirilimi", "momentum_devam", "asiri_gerilme")}
        taban = {"in": [], "out": []}

        for start in range(0, len(syms), 100):
            chunk = syms[start:start + 100]
            tickers = {yf_ticker(s, market): s for s in chunk}
            try:
                data = yf.download(list(tickers), period="10y", group_by="ticker",
                                   auto_adjust=True, progress=False, threads=True)
            except Exception as e:
                print("chunk hatası:", str(e)[:80])
                continue
            for ticker in tickers:
                try:
                    df = data[ticker] if len(tickers) > 1 else data
                    df = df.dropna(subset=["Close", "Volume", "High", "Low"])
                    if len(df) < 300:
                        continue
                    fwd = df["Close"].shift(-FWD) / df["Close"] - 1
                    donem = pd.Series(["in" if str(d) < SPLIT else "out" for d in df.index],
                                      index=df.index)
                    # taban çizgisi: TÜM günlerin ileri getirisi
                    for p in ("in", "out"):
                        taban[p].extend(fwd[donem == p].dropna().tolist())
                    for ad, mask in _series_setups(df, idx).items():
                        mask = mask.fillna(False)
                        for i in _dedup(mask):
                            f = fwd.iloc[i]
                            if pd.notna(f):
                                kayitlar[ad][donem.iloc[i]].append(float(f))
                except Exception:
                    continue
            time.sleep(1)

        sonuc[market] = {}
        for ad, kayit in kayitlar.items():
            sonuc[market][ad] = {}
            for p in ("in", "out"):
                r = pd.Series(kayit[p])
                b = pd.Series(taban[p])
                sonuc[market][ad][p] = {
                    "n": int(len(r)),
                    "medyan_pct": round(float(r.median()) * 100, 2) if len(r) else None,
                    "pozitif_oran": round(float((r > 0).mean()), 3) if len(r) else None,
                    "taban_medyan_pct": round(float(b.median()) * 100, 2) if len(b) else None,
                }
        print(f"\n=== {market} ===")
        for ad, d in sonuc[market].items():
            print(f"{ad}:")
            for p in ("in", "out"):
                s = d[p]
                print(f"  [{p:3}] n={s['n']:5} medyan %{s['medyan_pct']} "
                      f"(taban %{s['taban_medyan_pct']}) pozitif {s['pozitif_oran']}")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"split": SPLIT, "fwd_gun": FWD, "hizli": hizli,
                               "sonuc": sonuc}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\nYazıldı: {OUT}")


if __name__ == "__main__":
    run(hizli="--hizli" in sys.argv)
