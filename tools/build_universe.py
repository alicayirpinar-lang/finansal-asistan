"""Sembol evreni üretici (plan bölüm 3: BIST100 + S&P500 ≈ 600 sembol).

Wikipedia'dan bileşen listelerini çekip data/universe.json üretir. Aylık elle
çalıştırılır (plan: 'statik sözlük, aylık güncellenir'):

    python tools/build_universe.py

Varyant üretimi otomatiktir ve yanlış eşleşmeye karşı bilinçli muhafazakardır:
- Tek kelimelik varyant ancak >=5 harfse ve belirsiz-kelime listesinde değilse
  eklenir ("Target", "General", "Global" gibi isimler tam adla aranır).
- Eşleşme filter.py'de kelime sınırıyla yapılır (substring değil).
- Genişletilmiş evren TEMA almaz (bilinçli kısıt: 70 sembollü bir temanın tek
  Fed haberiyle kota yemesini önler); tema yolu el yapımı config.SYMBOLS'ta kalır.
"""
import io
import json
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

UA = {"User-Agent": "finansal-asistan/1.0 (kisisel arastirma)"}
OUT = Path(__file__).resolve().parent.parent / "data" / "universe.json"

# Tek başına aranırsa gürültü üreten isim kelimeleri (haber dilinde yaygın)
AMBIGUOUS_EN = {
    "general", "american", "united", "national", "international", "global",
    "standard", "first", "target", "progressive", "discover", "southern",
    "public", "universal", "digital", "service", "energy", "consumer",
    "capital", "financial", "republic", "alliance", "advance", "electronic",
    "match", "news", "live", "host", "extra", "state", "street", "west",
    "block", "smart", "delta", "union", "crown", "globe", "quest",
    "booking", "carnival", "mosaic", "waters", "dover", "everest", "tapestry",
}
AMBIGUOUS_TR = {
    "türk", "türkiye", "anadolu", "ulusal", "milli", "global", "yapı",
    "doğu", "batı", "ege", "marmara", "enerji", "petrol", "altın", "koza",
    "kalkınma", "yatırım", "gayrimenkul", "holding", "grup", "grubu",
}
# İngilizce sözlük kelimesi olan ticker'lar — varyant olarak kullanılamaz
TICKER_STOP = {
    "ball", "cost", "fast", "meta", "well", "dash", "open", "play", "spot",
    "nice", "real", "land", "pool", "main", "core", "data", "form", "fund",
    "gold", "life", "mind", "news", "path", "peak", "rare", "safe", "star",
    "step", "turn", "wave", "wise", "work", "care", "keys", "tech", "best",
}
# Kurallara takılan ama haberde geçen büyük isimler için elle ekler
EXTRA_VARIANTS = {
    "MMM": ["3m company"],
    "T": ["at&t"],
    "IBM": ["ibm"],
}
# Ünvan/legal ek kelimeleri (varyanttan atılır)
SUFFIX_EN = re.compile(
    r"\b(incorporated|inc\.?|corporation|corp\.?|company|co\.?|plc|ltd\.?|"
    r"group|holdings?|the)\b|\(.*?\)|,", re.IGNORECASE)
SUFFIX_TR = re.compile(
    r"\b(a\.?ş\.?|t\.?a\.?ş\.?|a\.?o\.?|anonim|şirketi|ortaklığı|ve|sanayii?|"
    r"ticaret|holding|yatırım)\b|\(.*?\)|,", re.IGNORECASE)


def _lower(s, tr=False):
    # Türkçe İ/I küçültmesi: İ→i, I→ı (Python .lower() İ'yi 'i̇' yapar — eşleşmeyi bozar)
    if tr:
        s = s.replace("İ", "i").replace("I", "ı")
    return s.lower()


def _clean_name(name, tr=False):
    s = name.replace(".", " ")
    s = (SUFFIX_TR if tr else SUFFIX_EN).sub(" ", s)
    return re.sub(r"\s+", " ", _lower(s, tr)).strip()


def _variants(ticker, name, tr=False):
    """Muhafazakar varyant seti: tam ad + (güvenliyse) ticker.

    Çok kelimeli isimlerden TEK kelime türetilmez (bilinçli: "Wells Fargo"dan
    "wells", "Steel Dynamics"ten "steel" üretmek yanlış eşleşme patlatır;
    haber dili zaten tam adı kullanır). Tek kelimelik tam adlar (Boeing, Apple)
    belirsiz-kelime kontrolünden geçerse kalır."""
    ambiguous = AMBIGUOUS_TR if tr else AMBIGUOUS_EN
    out = []
    clean = _clean_name(name, tr)
    words = clean.split()
    if len(words) == 1:
        if len(clean) >= 5 and clean not in ambiguous:
            out.append(clean)
    elif words:
        out.append(clean if len(words) <= 3 else " ".join(words[:3]))
    # Ticker'ın kendisi: BIST'te >=5, ABD'de >=4 harf (kısa ticker'lar kelime çakışır)
    t = ticker.lower()
    if len(t) >= (5 if tr else 4) and t not in ambiguous and t not in TICKER_STOP:
        out.append(t)
    # Hiç varyant kalmadıysa son çare: ünvanlı tam ad (2+ kelime, güvenli bigram)
    if not out:
        base = re.sub(r"\s+", " ", _lower(name.replace(".", " "), tr)).strip()
        if len(base.split()) >= 2:
            out.append(base)
    out.extend(EXTRA_VARIANTS.get(ticker, []))
    return sorted(set(v for v in out if len(v) >= 3))


def _wiki_tables(host, page):
    r = requests.get(f"https://{host}/w/api.php", headers=UA, timeout=30, params={
        "action": "parse", "page": page, "prop": "text",
        "format": "json", "formatversion": 2})
    r.raise_for_status()
    return pd.read_html(io.StringIO(r.json()["parse"]["text"]))


def fetch_sp500():
    tables = _wiki_tables("en.wikipedia.org", "List of S&P 500 companies")
    t = next(t for t in tables if "Symbol" in t.columns and "Security" in t.columns)
    out = {}
    for _, row in t.iterrows():
        ticker = str(row["Symbol"]).strip().replace(".", "-")  # BRK.B -> BRK-B (Yahoo formatı)
        name = str(row["Security"]).strip()
        out[ticker] = {
            "name": name, "market": "US",
            "sector": str(row.get("GICS Sector", "")).strip(),
            "variants": _variants(ticker, name, tr=False),
        }
    return out


def fetch_bist100():
    tables = _wiki_tables("tr.wikipedia.org",
                          "Borsa İstanbul'da işlem gören şirketler listesi")
    t = next(t for t in tables
             if "Kod" in t.columns and "Firma Adı" in t.columns and len(t) > 50)
    out = {}
    for _, row in t.iterrows():
        ticker = str(row["Kod"]).strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{4,6}", ticker):
            continue
        name = str(row["Firma Adı"]).strip()
        out[ticker] = {
            "name": name, "market": "BIST",
            "sector": str(row.get("Sektör", "")).strip(),
            "variants": _variants(ticker, name, tr=True),
        }
    return out


def main():
    sp500 = fetch_sp500()
    bist = fetch_bist100()
    print(f"S&P500: {len(sp500)} sembol, BIST100: {len(bist)} sembol")
    if len(sp500) < 400 or len(bist) < 80:
        print("HATA: kaynak listelerden biri şüpheli derecede kısa — dosya yazılmadı.")
        sys.exit(1)
    universe = {**sp500, **bist}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_at": date.today().isoformat(),
        "symbols": universe,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Yazıldı: {OUT} ({len(universe)} sembol)")
    # Göz kontrolü için örnekler
    for s in ["AAPL", "TGT", "GM", "LMT", "AEFES", "AKBNK", "KOZAL"]:
        if s in universe:
            print(f"  {s}: {universe[s]['variants']}")


if __name__ == "__main__":
    main()
