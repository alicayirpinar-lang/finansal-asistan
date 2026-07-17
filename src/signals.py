"""Teknik sinyal katmanı (Katman 4) — plan bölüm 6. AI kullanmaz, saf pandas.

Göstergeler: hacim z-skoru (20g, |z|>=3), RSI(14) aşırılığı (<25/>75),
MA20 kesişimi + hacim onayı (hacim_z>=1.5), 52 hafta zirve/dip yakınlığı (%2).
Gürültü kuralı: sembol ancak >=2 gösterge AYNI YÖNDE tetiklenirse gözleme girer.
Tüm semboller technical_signals'a yazılır (kurtarma planının 4. sinyali için);
gözlem filtresi sadece rapor sorgusunda uygulanır.
"""
import math

import pandas as pd
import yfinance as yf

from config import SYMBOLS
from src.prices import yf_ticker


def _rsi14(close):
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ru = up.ewm(alpha=1 / 14, adjust=False).mean()
    rd = down.ewm(alpha=1 / 14, adjust=False).mean()
    rs = ru / rd.replace(0, float("nan"))
    return 100 - 100 / (1 + rs)


def _clean(v):
    try:
        v = float(v)
        return None if (math.isnan(v) or math.isinf(v)) else round(v, 3)
    except (TypeError, ValueError):
        return None


def _analyze_one(df):
    """Tek sembolün OHLCV geçmişinden gösterge seti üret. Dönüş: dict veya None."""
    df = df.dropna(subset=["Close", "Volume", "High", "Low"])
    if len(df) < 60:
        return None
    close, vol = df["Close"], df["Volume"]

    vol_mean = vol.rolling(20).mean().iloc[-1]
    vol_std = vol.rolling(20).std().iloc[-1]
    volume_z = _clean((vol.iloc[-1] - vol_mean) / vol_std) if vol_std else None

    rsi = _clean(_rsi14(close).iloc[-1])

    ma20 = close.rolling(20).mean()
    cross_up = close.iloc[-2] <= ma20.iloc[-2] and close.iloc[-1] > ma20.iloc[-1]
    cross_dn = close.iloc[-2] >= ma20.iloc[-2] and close.iloc[-1] < ma20.iloc[-1]
    ma20_cross = bool(cross_up or cross_dn)

    hi52, lo52 = close.tail(252).max(), close.tail(252).min()
    pct_from_hi = _clean((hi52 - close.iloc[-1]) / hi52 * 100)
    pct_from_lo = _clean((close.iloc[-1] - lo52) / lo52 * 100)

    # Tetiklenen sinyaller: (isim, yön) — yön +1 yükseliş / -1 düşüş
    day_dir = 1 if close.iloc[-1] >= close.iloc[-2] else -1
    triggers = []
    if volume_z is not None and abs(volume_z) >= 3.0:
        triggers.append(("hacim_anomalisi", day_dir))
    if rsi is not None and rsi < 25:
        triggers.append(("rsi_asiri_satim", 1))
    if rsi is not None and rsi > 75:
        triggers.append(("rsi_asiri_alim", -1))
    if ma20_cross and volume_z is not None and volume_z >= 1.5:
        triggers.append(("ma20_kesisim", 1 if cross_up else -1))
    if pct_from_hi is not None and pct_from_hi <= 2.0:
        triggers.append(("52h_zirve_yakini", 1))
    if pct_from_lo is not None and pct_from_lo <= 2.0:
        triggers.append(("52h_dip_yakini", -1))

    # >=2 gösterge aynı yönde şartı (çoklu karşılaştırma gürültüsüne karşı)
    ups = [t for t in triggers if t[1] > 0]
    downs = [t for t in triggers if t[1] < 0]
    dominant = ups if len(ups) >= len(downs) else downs
    signal_count = len(dominant)
    severity = min(abs(volume_z or 0), 5) / 5
    gozlem_skoru = _clean(signal_count + severity) if signal_count >= 2 else 0.0

    return {
        "volume_z": volume_z, "rsi": rsi, "ma20_cross": ma20_cross,
        "pct_from_52w": pct_from_hi, "signal_count": signal_count,
        "gozlem_skoru": gozlem_skoru or 0.0,
        "_triggers": [t[0] for t in dominant],
        "_direction": "yukselis" if dominant is ups else "dusus",
    }


CHUNK = 100  # yf.download tek istekte bu kadar sembol (600'ü tek seferde istememek için)


def compute_signals(market):
    """Bir pazarın tüm sembollerini parçalı toplu indirip analiz et.

    Dönüş: technical_signals satırları (DB alanları) + rapor için ekstra alanlar.
    """
    symbols = [s for s, i in SYMBOLS.items() if i["market"] == market]
    rows = []
    for start in range(0, len(symbols), CHUNK):
        tickers = {yf_ticker(s, market): s for s in symbols[start:start + CHUNK]}
        try:
            data = yf.download(list(tickers), period="1y", group_by="ticker",
                               auto_adjust=True, progress=False, threads=True)
        except Exception:
            continue  # bir parça çökerse diğerleri devam eder
        for ticker, symbol in tickers.items():
            try:
                df = data[ticker] if len(tickers) > 1 else data
                result = _analyze_one(df)
                if result:
                    rows.append({"symbol": symbol, "market": market, **result})
            except Exception:
                continue
    return rows
