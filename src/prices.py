"""Fiyat verisi: yfinance sarmalayıcı. BIST sembolleri Yahoo'da '.IS' uzantılı.

NaN koruması: yfinance eksik veri döndürebilir; NaN JSON'a yazılamaz (Supabase
hata verir), bu yüzden tüm dönüşler None'a normalize edilir.
"""
import math

import pandas as pd
import yfinance as yf


def _clean(value, digits=4):
    try:
        v = float(value)
        return None if (math.isnan(v) or math.isinf(v)) else round(v, digits)
    except (TypeError, ValueError):
        return None


def yf_ticker(symbol, market):
    return f"{symbol}.IS" if market == "BIST" else symbol


def current_price(symbol, market):
    """Son fiyat; alınamazsa None (çağıran taraf pipeline'ı durdurmaz)."""
    try:
        t = yf.Ticker(yf_ticker(symbol, market))
        try:
            p = _clean(t.fast_info.last_price)
            if p:
                return p
        except Exception:
            pass
        hist = t.history(period="5d")
        if len(hist):
            return _clean(hist["Close"].dropna().iloc[-1])
    except Exception:
        pass
    return None


def market_snapshot(symbol, market):
    """Beyin promptları için kısa piyasa bağlamı (tez kalitesi fazı):
    güncel fiyat, 1 aylık değişim, 52h zirveye uzaklık, hacim z-skoru.
    'Zaten fiyatlanmış mı' sorusu ancak bu veriyle dürüstçe cevaplanabilir."""
    try:
        hist = yf.Ticker(yf_ticker(symbol, market)).history(period="1y")
        hist = hist.dropna(subset=["Close"])
        if len(hist) < 25:
            return None
        close, vol = hist["Close"], hist["Volume"]
        price = _clean(close.iloc[-1], 2)
        chg_1m = _clean((close.iloc[-1] / close.iloc[-22] - 1) * 100, 1)
        hi52 = close.tail(252).max()
        from_hi = _clean((hi52 - close.iloc[-1]) / hi52 * 100, 1)
        vol_std = vol.rolling(20).std().iloc[-1]
        volume_z = _clean((vol.iloc[-1] - vol.rolling(20).mean().iloc[-1]) / vol_std, 1) \
            if vol_std else None
        return {"price": price, "chg_1m_pct": chg_1m,
                "pct_from_52w_high": from_hi, "volume_z": volume_z}
    except Exception:
        return None


def atr14(symbol, market):
    """ATR(14) — stop mesafesi hesabı için (plan: stop = 2×ATR)."""
    try:
        hist = yf.Ticker(yf_ticker(symbol, market)).history(period="2mo")
        hist = hist.dropna(subset=["High", "Low", "Close"])
        if len(hist) < 15:
            return None
        h, l, c = hist["High"], hist["Low"], hist["Close"]
        prev_c = c.shift(1)
        tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
        return _clean(tr.rolling(14).mean().iloc[-1])
    except Exception:
        return None
