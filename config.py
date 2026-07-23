"""Yapılandırma: sembol sözlüğü (BIST + ABD), RSS kaynakları, filtre parametreleri.

Sembol evreni iki katmanlı (plan bölüm 3-4, ~600 sembol geniş tarama):
- CORE_SYMBOLS: el yapımı 30 sembol — zengin varyantlar + TEMA etiketleri
  (tema yolu sadece bu katmanda çalışır; USO+XOM+TUPRS aynı anda yakalanır)
- data/universe.json: BIST100 + S&P500 otomatik evreni (tools/build_universe.py,
  aylık elle güncellenir) — ad/ticker eşleşmesi + sektörden türetilmiş tema
  etiketleri (kullanıcı kararı: tüm evren iki yola da tabi). Tema günlerinde
  kota koruması mevcut frenlerde: MAX_THESES_PER_RUN, 48s sembol tekrarı yok,
  günlük Gemini tavanı, red-team. El yapımı tanımlar evrendekini ezer.
"""
import json as _json
from pathlib import Path as _Path

# --- Sembol sözlüğü (çekirdek katman) -------------------------------------
# variants: haber metninde aranan küçük-harf ad varyasyonları (kelime sınırlı)
# themes: tema yolu eşleşmesi için etiketler

CORE_SYMBOLS = {
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


def _load_universe():
    """data/universe.json'dan genişletilmiş evreni yükle; dosya yoksa boş dön
    (sistem çekirdek 30 sembolle çalışmaya devam eder — evren opsiyonel katman)."""
    path = _Path(__file__).resolve().parent / "data" / "universe.json"
    try:
        raw = _json.loads(path.read_text(encoding="utf-8"))["symbols"]
    except (OSError, ValueError, KeyError):
        return {}
    return {
        sym: {"name": info["name"], "market": info["market"],
              "sector": info.get("sector", ""),
              "themes": info.get("themes", []),
              "variants": info.get("variants", [])}
        for sym, info in raw.items()
    }


# Birleşik evren: el yapımı çekirdek her zaman kazanır (varyant/tema kalitesi)
SYMBOLS = {**_load_universe(), **CORE_SYMBOLS}

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

# --- Faz 12 KAP entegrasyonu: rutin/idari bildirim süzgeci ------------------
# KAP'ın ODA (Özel Durum Açıklaması) sınıfı çok geniş — bu standart konu
# başlıkları piyasayı hareket ettirme ihtimali düşük idari işlemler (canlı
# örneklemle görüldü: pay geri alım, kredi notu, komite/ünvan değişikliği vb.)
# Elenenler dışındakiler mevcut alaka skoru + Gemini triyajdan geçer — RSS
# haberlerinden farklı bir "otomatik güven" iddiası yok, sadece gürültü azaltma.
RUTIN_KAP_KONU = [
    "payların geri alınmasına ilişkin bildirim", "kredi derecelendirmesi",
    "yönetim kurulu komiteleri", "bağımsız denetim kuruluşunun belirlenmesi",
    "ilişkili taraf işlemleri", "ünvan değişikliği",
    "genel kurul işlemlerine ilişkin bildirim", "esas sözleşme tadili",
    # 23 Temmuz 2026 bulgusu: en yüksek hacimli KAP kategorisi (bir günde
    # 384 bildirimin 131'i) hiç filtrelenmiyordu — rutin tahvil/borçlanma
    # ihracı, triyaj kotasını (25) dolduruyordu.
    "pay dışında sermaye piyasası aracı işlemlerine ilişkin bildirim",
    "ihraç tavanına ilişkin bildirim",
    "kayıtlı sermaye tavanı işlemlerine ilişkin bildirim",
    "kurumsal yönetim ilkelerine uyum derecelendirmesi",
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
MAX_THESES_PER_RUN    = 8       # tek çalıştırmada üretilecek max yeni tez (faz 12: 5->8, günlük kota sayacı zaten üst sınırı korur)
FRESHNESS_HALFLIFE_H  = 12      # tazelik yarı ömrü (saat)

# Faz 12 D — çeşitlilik onarımı: triyaj tavanı tek toplu çağrı olduğu için
# yükseltmenin kota maliyeti yok; küme başı sınır tek haberin (örn. tek ECB
# haberinin 10+ bankaya yayılması) tüm tavanı yemesini önler.
TRIAGE_BATCH_SIZE     = 25      # tek triyaj çağrısına giden max olay
TRIAGE_KUME_BASI_MAKS = 2       # aynı haber kümesinden (cluster_id) triyaja en fazla kaç olay girer

KATEGORI_AGIRLIK = {"jeopolitik": 1.0, "makro": 0.9, "sirket": 0.8, "sektor": 0.7, "takvimli": 0.6}

GEMINI_THROTTLE_SECONDS = 6     # RPM limiti için çağrılar arası bekleme (plan bölüm 11)

# --- Faz 12 A: Teknik radar (Gemini'siz takip edilen pozisyon) -------------
TEKNIK_RADAR_MIN_SKOR   = 70    # rapordaki "büyük hareket" bildirimiyle aynı kalite bandı
TEKNIK_RADAR_SOGUMA_GUN = 10    # aynı sembolde yeni pozisyon açmadan önce bekleme (backtest DEDUP_GUN uyumlu)
TEKNIK_RADAR_GUNLUK_CAP = 5     # pazar başına (rapor koşusu) en fazla yeni pozisyon

# --- Faz 12 B: İkinci derece akıl yürütme (füzyon şartlı) -------------------
IKINCI_DERECE_MIN_KAYNAK = 3    # eşleşmeyen kümenin adaya girmesi için min. kaynak sayısı (yaygınlık = önem sinyali)
# 22 Temmuz 2026 bulgusu: build_events() tazelik çürümesi uyguluyor ama
# unmatched_clusters() uygulamıyordu — aylık bir "güncel petrol fiyatı"
# makalesi (Google News'in her aramada tekrar sunduğu evergreen sayfa) her
# koşuda "önemli" sayılıp Gemini'ye gönderiliyor, hep aynı sembollere
# bağlanıyordu. Bu yaş sınırının üstündeki kümeler B'ye hiç girmez.
IKINCI_DERECE_MAKS_YAS_SAAT = 48
IZLEME_TTL_GUN            = 15  # füzyon geçemeyen bağ, teknik teyit gelmezse bu kadar gün sonra düşer
