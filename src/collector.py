"""Haber toplama: tema bazlı RSS kaynaklarından ham haber havuzu.

Her dış çağrı 30sn timeout + sessiz hata (plan bölüm 11: pipeline durmaz).
"""
import time
from datetime import datetime, timezone

import feedparser

from config import RSS_SOURCES

FETCH_TIMEOUT = 30


def _parse_time(entry):
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def collect_news():
    """Tüm kaynakları gez, ham haber listesi döndür. Kaynak hatası pipeline'ı durdurmaz."""
    items, errors = [], []
    for source_name, url, lang, reliability in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                errors.append((source_name, str(feed.bozo_exception)))
                continue
            for entry in feed.entries:
                title = (entry.get("title") or "").strip()
                if len(title) < 15:  # başlıksız/çok kısa: gürültü, ele
                    continue
                items.append({
                    "source": source_name,
                    "reliability": reliability,
                    "language": lang,
                    "title": title,
                    "url": entry.get("link"),
                    "summary": (entry.get("summary") or "")[:500],
                    "published_at": _parse_time(entry),
                })
        except Exception as e:
            errors.append((source_name, str(e)))
        time.sleep(0.5)  # kaynaklara nazik davran
    return items, errors
