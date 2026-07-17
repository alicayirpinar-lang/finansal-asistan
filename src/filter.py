"""Aşama 1 filtresi: dedup -> varlık/tema eşleştirme -> alaka skoru -> kuyruk ayrımı.

Plan bölüm 4. v1'de dedup sadece rapidfuzz başlık benzerliği
(embedding kümeleme buluta taşıma aşamasında eklenecek).
"""
import math
from datetime import datetime, timezone

from rapidfuzz import fuzz

from config import (
    SYMBOLS, THEME_KEYWORDS, CRITICAL_KEYWORDS,
    DEDUP_TITLE_THRESHOLD, RELEVANCE_MIN_SCORE,
    FRESHNESS_HALFLIFE_H, KATEGORI_AGIRLIK,
)


def dedup(items):
    """Benzer başlıkları kümele. Temsilci = en güvenilir kaynaklı/en erken haber.

    Küme büyüklüğü yaygınlık_çarpanı olarak alaka skoruna girer (plan: çok
    kaynaklı haber = muhtemelen önemli haber).
    """
    clusters = []
    for item in items:
        placed = False
        for cluster in clusters:
            if fuzz.token_set_ratio(item["title"].lower(),
                                    cluster["rep"]["title"].lower()) >= DEDUP_TITLE_THRESHOLD:
                cluster["members"].append(item)
                if item["reliability"] > cluster["rep"]["reliability"]:
                    cluster["rep"] = item
                placed = True
                break
        if not placed:
            clusters.append({"rep": item, "members": [item]})
    return clusters


def _match_symbols(text):
    """Metni sembollere bağla. Dönüş: {symbol: yakınlık} (doğrudan=1.0, tema=0.4)."""
    text = text.lower()
    matches = {}
    for symbol, info in SYMBOLS.items():
        if any(v in text for v in info["variants"]):
            matches[symbol] = 1.0
    for theme, keywords in THEME_KEYWORDS.items():
        if any(k in text for k in keywords):
            for symbol, info in SYMBOLS.items():
                if theme in info["themes"]:
                    matches.setdefault(symbol, 0.4)
    return matches


def _guess_category(text):
    text = text.lower()
    if any(k in text for k in ("savaş", "war", "jeopolitik", "geopolit", "füze", "nato", "ambargo", "embargo")):
        return "jeopolitik"
    if any(k in text for k in ("fed ", "tcmb", "faiz", "rate", "enflasyon", "inflation", "merkez bankası")):
        return "makro"
    if any(k in text for k in ("bilanço", "earnings", "kar", "profit", "ceo", "dava", "lawsuit", "ihale")):
        return "sirket"
    return "sektor"


def is_critical(text):
    text = text.lower()
    return any(k in text for k in CRITICAL_KEYWORDS)


def _freshness(published_at):
    if not published_at:
        return 0.5
    age_h = max(0.0, (datetime.now(timezone.utc) - published_at).total_seconds() / 3600)
    return math.pow(0.5, age_h / FRESHNESS_HALFLIFE_H)


def build_events(clusters, portfolio_symbols=frozenset()):
    """Kümelerden skorlu olay listesi üret (sembol başına bir olay)."""
    events = []
    for cluster in clusters:
        rep = cluster["rep"]
        text = rep["title"] + " " + rep.get("summary", "")
        matches = _match_symbols(text)
        if not matches:
            continue
        category = _guess_category(text)
        critical = is_critical(text)
        spread = min(1.0 + 0.05 * (len(cluster["members"]) - 1), 1.5)  # yaygınlık, üst sınırlı
        for symbol, proximity in matches.items():
            score = (KATEGORI_AGIRLIK[category] * proximity * rep["reliability"]
                     * _freshness(rep["published_at"]) * spread)
            if symbol in portfolio_symbols:
                score *= 1.2  # portföy bonusu
            if score < RELEVANCE_MIN_SCORE and not critical:
                continue
            events.append({
                "symbol": symbol,
                "market": SYMBOLS[symbol]["market"],
                "category": category,
                "relevance_score": round(score, 3),
                "priority_lane": "kritik" if critical else "normal_kuyruk",
                "title": rep["title"],
                "summary": rep.get("summary", ""),
                "url": rep.get("url"),
                "source": rep["source"],
                "source_count": len(cluster["members"]),
                "published_at": rep["published_at"],
            })
    # kritikler öne, sonra skora göre
    events.sort(key=lambda e: (e["priority_lane"] != "kritik", -e["relevance_score"]))
    return events
