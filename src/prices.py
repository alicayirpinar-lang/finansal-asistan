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
