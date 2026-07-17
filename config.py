"""v1 yapılandırması: sembol sözlüğü (BIST + ABD), RSS kaynakları, filtre parametreleri.

Sembol sözlüğü plan bölüm 4'teki 'statik sözlük' yaklaşımının dar (v1) hali.
Geniş taramaya (600 sembol) geçerken bu yapı Supabase `symbols` tablosuna taşınacak.
"""

# --- Sembol sözlüğü -------------------------------------------------------
# variants: haber metninde aranan küçük-harf ad varyasyonları
# themes: tema yolu eşleşmesi için etiketler

SYMBOLS = {
    # ABD
    "XOM":   {"name": "Exxon Mobil",      "market": "US",   "themes": ["enerji", "petrol"],           "variants": ["exxon", "exxonmobil"]},
    "CVX":   {"name": "Chevron",           "market": "US",   "themes": ["enerji", "petrol"],           "variants": ["chevron"]},
    "USO":   {"name": "US Oil Fund ETF",   "market": "US",   "themes": ["enerji", "petrol"],           "variants": ["uso ", "us oil fund"]},
    "AAPL":  {"name": "Apple",             "market": "US",   "themes": ["teknoloji"],                  "variants": ["apple"]},
    "MSFT":  {"name": "Microsoft",         "market": "US",   "themes": ["teknoloji"],                  "variants": ["microsoft"]},
    "NVDA":  {"name": "Nvidia",            "market": "US",   "themes": ["teknoloji", "yapay_zeka"],    "variants": ["nvidia"]},
    "JPM":   {"name": "JPMorgan",          "market": "US",   "themes": ["banka", "faiz"],              "variants": ["jpmorgan", "jp morgan"]},
    "BAC":   {"name": "Bank of America",   "market": "US",   "themes": ["banka", "faiz"],              "variants": ["bank of america"]},
    "BA":    {"name": "Boeing",            "market": "US",   "themes": ["havacilik", "savunma"],       "variants": ["boeing"]},
    "LMT":   {"name": "Lockheed Martin",   "market": "US",   "themes": ["savunma"],                    "variants": ["lockheed"]},
    "PFE":   {"name": "Pfizer",            "market": "US",   "themes": ["saglik"],                     "variants": ["pfizer"]},
    "WMT":   {"name": "Walmart",           "market": "US",   "themes": ["perakende"],                  "variants": ["walmart"]},
    "TSLA":  {"name": "Tesla",             "market": "US",   "themes": ["otomotiv", "teknoloji"],      "variants": ["tesla"]},
    "GLD":   {"name": "SPDR Gold ETF",     "market": "US",   "themes": ["altin", "guvenli_liman"],     "variants": ["gold etf", "altın ons"]},
    "CAT":   {"name": "Caterpillar",       "market": "US",   "themes": ["sanayi", "insaat"],           "variants": ["caterpillar"]},
    # BIST
    "THYAO": {"name": "Türk Hava Yolları", "market": "BIST", "themes": ["havacilik", "turizm"],        "variants": ["türk hava yolları", "thy", "turkish airlines"]},
    "TUPRS": {"name": "Tüpraş",            "market": "BIST", "themes": ["enerji", "petrol"],           "variants": ["tüpraş", "tupras"]},
    "ASELS": {"name": "Aselsan",           "market": "BIST", "themes": ["savunma"],                    "variants": ["aselsan"]},
    "GARAN": {"name": "Garanti BBVA",      "market": "BIST", "themes": ["banka", "faiz"],              "variants": ["garanti bbva", "garanti bankası", "garan hisse"]},
    "AKBNK": {"name": "Akbank",            "market": "BIST", "themes": ["banka", "faiz"],              "variants": ["akbank"]},
    "ISCTR": {"name": "İş Bankası",        "market": "BIST", "themes": ["banka", "faiz"],              "variants": ["iş bankası", "isbank"]},
    "KCHOL": {"name": "Koç Holding",       "market": "BIST", "themes": ["holding", "sanayi"],          "variants": ["koç holding"]},
    "SAHOL": {"name": "Sabancı Holding",   "market": "BIST", "themes": ["holding", "banka"],           "variants": ["sabancı"]},
    "EREGL": {"name": "Ereğli Demir Çelik","market": "BIST", "themes": ["sanayi", "celik"],            "variants": ["erdemir", "ereğli"]},
    "SISE":  {"name": "Şişecam",           "market": "BIST", "themes": ["sanayi"],                     "variants": ["şişecam", "sisecam"]},
    "BIMAS": {"name": "BİM",               "market": "BIST", "themes": ["perakende"],                  "variants": ["bim birleşik", "bim mağaza"]},
    "TCELL": {"name": "Turkcell",          "market": "BIST", "themes": ["telekom", "teknoloji"],       "variants": ["turkcell"]},
    "FROTO": {"name": "Ford Otosan",       "market": "BIST", "themes": ["otomotiv"],                   "variants": ["ford otosan"]},
    "TOASO": {"name": "Tofaş",             "market": "BIST", "themes": ["otomotiv"],                   "variants": ["tofaş", "tofas"]},
    "PETKM": {"name": "Petkim",            "market": "BIST", "themes": ["enerji", "petrokimya"],       "variants": ["petkim"]},
}

# Tema yolu: haberde bu kelimeler geçerse temaya etiketli TÜM semboller aday olur
THEME_KEYWORDS = {
    "enerji":       ["petrol", "opec", "brent", "doğalgaz", "hürmüz", "crude oil", "natural gas", "rafineri"],
    "petrol":       ["petrol fiyat", "oil price", "varil", "barrel", "opec"],
    "savunma":      ["savaş", "war", "füze", "missile", "nato", "saldırı", "attack", "savunma sanayi", "askeri", "military"],
    "banka":        ["faiz karar", "merkez bankası", "fed ", "tcmb", "interest rate", "enflasyon", "inflation", "kredi"],
    "faiz":         ["faiz karar", "rate decision", "rate cut", "rate hike", "sıkılaşma"],
    "teknoloji":    ["çip", "chip", "semiconductor", "yapay zeka", "artificial intelligence", "ihracat kısıt", "export control"],
    "yapay_zeka":   ["yapay zeka", "artificial intelligence", "ai model", "gpu"],
    "havacilik":    ["uçak", "aircraft", "havayolu", "airline", "uçuş yasağı", "hava sahası", "airspace"],
    "saglik":       ["ilaç", "drug", "fda", "onay", "klinik deney", "clinical trial"],
    "perakende":    ["tüketici harcama", "consumer spending", "perakende satış", "retail sales"],
    "otomotiv":     ["otomobil satış", "elektrikli araç", "electric vehicle", "ötv", "tarife", "tariff"],
    "sanayi":       ["sanayi üretim", "industrial production", "pmi", "ihracat", "hammadde"],
    "celik":        ["çelik", "steel", "demir cevheri", "iron ore", "kota", "anti-damping"],
    "altin":        ["altın", "gold", "ons", "güvenli liman", "safe haven"],
    "guvenli_liman":["jeopolitik risk", "geopolitical risk", "belirsizlik"],
    "telekom":      ["telekom", "5g", "frekans ihale"],
    "turizm":       ["turizm", "tourism", "rezervasyon", "seyahat yasağı"],
    "holding":      [],
    "insaat":       ["altyapı paketi", "infrastructure", "inşaat"],
    "petrokimya":   ["petrokimya", "nafta"],
}

# Kritik hızlı yol: bu kelimeler geçen haber kuyruğu atlar (plan bölüm 4)
CRITICAL_KEYWORDS = [
    "savaş ilan", "declares war", "war declared",
    "ambargo", "embargo",
    "boğaz kapat", "strait clos", "hürmüz kapat",
    "olağanüstü faiz", "emergency rate",
    "askeri operasyon başla", "military operation launch",
    "nükleer", "nuclear strike",
    "sıkıyönetim", "martial law",
    "temerrüt", "default on debt",
]

# --- RSS kaynakları (tema bazlı, plan bölüm 4) ----------------------------
GOOGLE_NEWS_TR = "https://news.google.com/rss/search?q={q}&hl=tr&gl=TR&ceid=TR:tr"
GOOGLE_NEWS_EN = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

RSS_SOURCES = [
    # (kaynak_adı, url, dil, güvenilirlik 0-1)
    ("gnews_tr_petrol",    GOOGLE_NEWS_TR.format(q="petrol+OPEC+fiyat"),          "tr", 0.6),
    ("gnews_tr_faiz",      GOOGLE_NEWS_TR.format(q="TCMB+faiz+karar%C4%B1"),      "tr", 0.6),
    ("gnews_tr_savunma",   GOOGLE_NEWS_TR.format(q="savunma+sanayi+ihale"),       "tr", 0.6),
    ("gnews_tr_borsa",     GOOGLE_NEWS_TR.format(q="borsa+istanbul+hisse"),       "tr", 0.6),
    ("gnews_en_oil",       GOOGLE_NEWS_EN.format(q="oil+prices+OPEC"),            "en", 0.6),
    ("gnews_en_fed",       GOOGLE_NEWS_EN.format(q="Federal+Reserve+rates"),      "en", 0.6),
    ("gnews_en_geopol",    GOOGLE_NEWS_EN.format(q="geopolitical+tension+market"),"en", 0.6),
    ("gnews_en_tech",      GOOGLE_NEWS_EN.format(q="semiconductor+export+chips"), "en", 0.6),
    ("bloomberght",        "https://www.bloomberght.com/rss",                     "tr", 1.0),
    ("aa_ekonomi",         "https://www.aa.com.tr/tr/rss/default?cat=ekonomi",    "tr", 1.0),
]

# --- Filtre parametreleri --------------------------------------------------
DEDUP_TITLE_THRESHOLD = 85      # rapidfuzz benzerlik eşiği (0-100)
RELEVANCE_MIN_SCORE   = 0.25    # bunun altındaki olaylar Aşama 2'ye gitmez
MAX_THESES_PER_RUN    = 5       # tek çalıştırmada üretilecek max yeni tez
FRESHNESS_HALFLIFE_H  = 12      # tazelik yarı ömrü (saat)

KATEGORI_AGIRLIK = {"jeopolitik": 1.0, "makro": 0.9, "sirket": 0.8, "sektor": 0.7, "takvimli": 0.6}

GEMINI_THROTTLE_SECONDS = 6     # RPM limiti için çağrılar arası bekleme (plan bölüm 11)
