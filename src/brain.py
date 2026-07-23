"""Finansal beyin: taslak zincir -> kendini eleştiri (red-team) -> birleştirme (kod).

Plan bölüm 5. v1'de function-calling araçları yok (faz 6'da eklenecek);
red-team bu yüzden taban oranına "veri yok" der — halüsinasyon kuralı gereği.
"""
import json
import os
import time

from google import genai

from config import GEMINI_THROTTLE_SECONDS
from src import storage

_ORDER = {"dusuk": 0, "orta": 1, "yuksek": 2}
_client = None
_last_call = 0.0

# gemini-flash-latest alias sessizce en yeni/en cimri modele kayabiliyor
# (gemini-3.5-flash = 20 istek/gün) — sabit sürüme pinlendi. Asla -latest
# kullanma (faz 12 kota kök nedeni).
DEFAULT_MODEL = "gemini-3.5-flash-lite"

# 22 Temmuz 2026 dersi: sabit pin de tek başına yeterli değil — gemini-2.5-flash
# Google tarafından "yeni kullanıcılara kapatıldı" (404 NOT_FOUND), sistem 12+
# saat boyunca sessizce sıfır tez üretti (canlı doğrulanan olay). Artık kısa bir
# düşüş sırası var: model kalıcı olarak kullanılamıyorsa (404/NOT_FOUND) ya da
# günlük kotası bittiyse (PerDay), OTOMATİK sıradaki adaya geçilir. Bir kez
# başarılı olan model o çalıştırma boyunca sabitlenir (tez içi tutarlılık için —
# aynı tezin taslağı ve red-team'i farklı modellerden çıkmasın).
FALLBACK_MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-lite-latest"]
_resolved_model = None

# Bu çalıştırmada (fresh process) kaç Gemini denemesi başarılı/başarısız oldu
# — sistemik hata tespiti için (bkz. sistemik_hata_kontrolu). 22 Temmuz 2026
# olayının imzası tam olarak buydu: onlarca deneme, hepsi başarısız, hiç kimse
# fark etmedi çünkü hiçbir yerde toplanmıyordu.
_basarili_sayisi = 0
_basarisiz_sayisi = 0
GEMINI_HATA_ESIGI = 5  # bu kadar denemeden sonra başarı hâlâ sıfırsa sistemik say

# 22 Temmuz 2026: günlük sabit sayı tavanı (DAILY_GEMINI_CAP) kaldırıldı — eski
# bir varsayıma (250/gün) dayanıyordu, gerçek ücretsiz limit artık 500/gün.
# Yerine ÇALIŞTIRMA-BAŞI bir sonsuz-döngü freni geldi: normal sağlıklı bir koşu
# ~18-26 çağrı yapar (1 triyaj + 1 ikinci-derece + en fazla 8 tez × ~2-3 çağrı);
# 60, bunun rahat üstünde ama bir kod hatası binlerce çağrı denemeye kalkarsa
# hemen durdurur. Google'ın kendi 500 RPD sınırı + model düşüş sırası zaten
# gerçek günlük hacmin doğal freni.
MAX_ATTEMPTS_PER_RUN = 60


def too_many_attempts_this_run():
    return (_basarili_sayisi + _basarisiz_sayisi) >= MAX_ATTEMPTS_PER_RUN


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def _log_attempt(call_type, basarili):
    """Her gerçek Gemini HTTP denemesini (başarılı/başarısız) kaydeder — eski
    tasarımda sadece başarılı çağrılar sayılıyordu, retry'lar ve exception'a
    düşen denemeler sayaçta görünmüyordu (faz 12 kota körlüğü kök nedeni).
    basarili bilgisi ayrıca tutulur — kota tavanı SADECE başarılıları sayar
    (bkz. storage.gemini_basarili_calls_today, 22 Temmuz ikinci kesinti dersi)."""
    try:
        storage.log_gemini_call(call_type, basarili=basarili)
    except Exception:
        pass  # kota kaydı başarısız oldu diye ana akış durmasın


def circuit_acik_mi():
    """Bu çalıştırmada Gemini tamamen ölü mü (≥GEMINI_HATA_ESIGI deneme, hiçbiri
    başarılı değil)? Açıksa main.py kalan olayları denemeden arşivler —
    dakikalarca ölü bir servise vurmak yerine 30 dk sonraki koşuya bırakılır
    (o koşu, bu sayaçlar fresh process'te sıfırlandığı için baştan dener)."""
    return _basarisiz_sayisi >= GEMINI_HATA_ESIGI and _basarili_sayisi == 0


def _adaylar():
    """Denenecek modeller, öncelik sırasıyla: bu çalıştırmada zaten başarılı
    olan (varsa) ya da env/varsayılan → sonra düşüş sırası. Kalıcı olarak
    çözülmüş model bile listede kalır — koşu ortasında o modelin kotası
    biterse (PerDay) sıradaki adaya düşülebilsin."""
    ilk = _resolved_model or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    return [ilk] + [m for m in FALLBACK_MODELS if m != ilk]


def _call(prompt, call_type="genel"):
    """Throttle'lı Gemini çağrısı. Model kalıcı olarak kullanılamıyorsa
    (404/NOT_FOUND) ya da günlük kotası bittiyse (PerDay) hemen sıradaki
    adaya geçer (tekrar denemek sadece zaman/kota kaybettirir); geçici
    (RPM/503) hatalarda aynı modelde 2 kez yeniden dener."""
    global _last_call, _resolved_model, _basarili_sayisi, _basarisiz_sayisi
    last_err = None
    for model in _adaylar():
        for attempt in range(3):
            wait = GEMINI_THROTTLE_SECONDS - (time.time() - _last_call)
            if wait > 0:
                time.sleep(wait)
            try:
                resp = _get_client().models.generate_content(model=model, contents=prompt)
                _last_call = time.time()
                _log_attempt(call_type, basarili=True)
                _resolved_model = model
                _basarili_sayisi += 1
                return resp.text
            except Exception as e:
                _last_call = time.time()
                _log_attempt(call_type, basarili=False)
                _basarisiz_sayisi += 1
                last_err = e
                kalici_hata = any(k in str(e) for k in ("NOT_FOUND", "404", "PerDay"))
                if not kalici_hata and any(code in str(e) for code in ("429", "503")) and attempt < 2:
                    time.sleep(15 * (attempt + 1))  # geçici yoğunluk: bekle ve aynı modeli tekrar dene
                    continue
                break  # bu modelde kalıcı hata: sıradaki adaya geç
    raise last_err


def sistemik_hata_kontrolu(kaynak):
    """Bu çalıştırmada yeterli sayıda Gemini denemesi olup HİÇBİRİ başarılı
    olmadıysa (GEMINI_HATA_ESIGI), bu izole bir hata değil sistemik bir
    sorundur (model kaldırılmış, API anahtarı geçersiz, proje silinmiş vb.)
    — 22 Temmuz 2026'da tam olarak bu oldu ve 12+ saat fark edilmedi. Kritik
    hata kaydı + Telegram uyarısı gönderir. main.py/tracker.py/report.py'nin
    run() sonunda çağrılması için tasarlandı, kendi hatalarını yutar."""
    if not (_basarisiz_sayisi >= GEMINI_HATA_ESIGI and _basarili_sayisi == 0):
        return
    mesaj = (f"bu çalıştırmada {_basarisiz_sayisi} Gemini denemesinin TAMAMI "
             f"başarısız oldu (0 başarılı) — model kaldırılmış, kota bitmiş "
             f"ya da API anahtarı geçersiz olabilir.")
    try:
        storage.log_error(kaynak, mesaj, seviye="kritik")
    except Exception:
        pass
    try:
        from src import notifier
        notifier.send(f"⚠️ SİSTEM HATASI ({kaynak})\n{mesaj}\nSitedeki /hatalar sayfasına bak.",
                      tur="sistem_hatasi")
    except Exception:
        pass  # bildirim de gidemiyorsa en azından hata kaydı DB'de kaldı


def _parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


TRIAGE_PROMPT = """Sen bir finans masası editörüsün. Aşağıdaki numaralı haber olaylarından
hangilerinin GERÇEK bir yatırım tezi adayı olduğuna karar ver.

ELE (gecer=false) şu durumlarda:
- Rutin açıklama, temenni, ziyaret, protokol haberi (örn. bakan/yönetici genel konuşması)
- Geriye dönük özet, haftalık/aylık performans değerlendirmesi ("bu hafta piyasalar...")
- Yeni bilgi içermeyen genel yorum veya zaten haftalardır bilinen durumun tekrarı
- Haberin sembolle bağı zayıf/dolaylı (yerel/alakasız bir olaydan zorlama bağlantı)

GEÇİR (gecer=true) şu durumlarda:
- Somut ve yeni katalizör: bilanço/kâr sürprizi, ihale, sözleşme, regülasyon, arz şoku,
  üretim kesintisi, birleşme/satın alma, yaptırım, faiz/enflasyon sürprizi
- Şüphede kaldıysan GEÇİR (ikinci savunma hattı var).

OLAYLAR:
{events}

SADECE geçerli JSON döndür:
[{{"no": 1, "gecer": true/false, "neden": "5-10 kelime"}}]"""


DRAFT_PROMPT = """Sen deneyimli bir finansal analistsin. Aşağıdaki haber olayı için sebep-sonuç zinciri kur.

OLAY:
Başlık: {title}
Özet: {summary}
İlgili sembol: {symbol} ({name}, {market})
Kategori: {category}
Kaç bağımsız kaynak verdi: {source_count}

PİYASA DURUMU ({symbol}):
{snapshot}

ÖN TEST — zincir kurmadan önce cevapla:
Bu haber, {symbol} için YENİ ve fiyat etkisi taşıyan bilgi içeriyor mu? Şu durumlarda
içermiyordur: haber olmasaydı da aynı tez yazılabiliyorsa; bağ dolaylı/zorlamaysa
(yerel bir olaydan küresel şirkete atlama gibi); sadece bilinen durumun tekrarıysa.
İçermiyorsa SADECE şunu döndür: {{"tez_yok": true, "neden": "1 cümle"}}

KURALLAR:
- Her zincir adımı tek bir SOMUT mekanizma anlatır ve kendi güven seviyesini taşır.
  "Olumlu etkileyebilir" gibi belirsiz ifadeler mekanizma değildir.
- Zincirin son adımı sembole ÖZGÜ olmalı (genel piyasa yorumu tez değildir).
- Güven değerleri SADECE şunlar olabilir: "dusuk", "orta", "yuksek".
- Toplam güven zincirin EN ZAYIF halkasına göre belirlenir, ortalamaya göre değil.
- Emin olmadığın şeyi yüksek güvenle işaretleme. Abartılı hedef verme; {market} piyasasında
  bu tür olaylar için gerçekçi büyüklük aralığı kullan. {buyukluk_kural}
- PİYASA DURUMU'nu dikkate al: fiyat olayı zaten yansıtmış görünüyorsa güveni düşür.
- SADECE geçerli JSON döndür, başka hiçbir şey yazma.

JSON ŞEMASI:
{{
  "zincir": [{{"adim_no": 1, "mekanizma": "...", "guven": "dusuk|orta|yuksek", "dayanak": "..."}}],
  "yon": "yukselis|dusus",
  "buyukluk_araligi_pct": [alt, ust],
  "ufuk": "gun|hafta|ay",
  "ufuk_deger": <sayı, ufuk biriminden>,
  "taslak_guven": "dusuk|orta|yuksek"
}}"""

REDTEAM_PROMPT = """Sen şüpheci bir risk yöneticisisin. Görevin aşağıdaki yatırım tezini ÇÜRÜTMEYE çalışmak.
Sana tezin güven skoru bilerek verilmedi; kendi bağımsız değerlendirmeni yap.

OLAY: {title}
SEMBOL: {symbol} ({market})
ZİNCİR: {chain}
BEKLENTİ: {direction}, %{low}-{ust} aralığında, ufuk: {horizon}

PİYASA DURUMU ({symbol}):
{snapshot}

9 SORUYU SIRAYLA CEVAPLA. Elinde veri olmayan soruda dürüstçe "veri yok" yaz — SAYI UYDURMA.
"zaten_fiyatlanmis_mi" sorusunda PİYASA DURUMU'ndaki fiyat hareketini kanıt olarak kullan.
Güven değerleri SADECE: "dusuk", "orta", "yuksek". SADECE geçerli JSON döndür.

JSON ŞEMASI:
{{
  "onemlilik": {{"onemli_mi": true/false, "aciklama": "bu olay bu şirketin değeri için gerçekten önemli mi, yoksa dolaylı/önemsiz mi"}},
  "en_zayif_halka": {{"adim_no": <n>, "aciklama": "..."}},
  "zaten_fiyatlanmis_mi": {{"cevap": "evet|hayir|belirsiz", "kanit": "..."}},
  "alternatif_aciklama": {{"var_mi": true/false, "aciklama": "..."}},
  "taban_orani": {{"vaka_sayisi": <n veya null>, "basari_orani_pct": <n veya null>, "kaynak": "genel bilgi|veri yok"}},
  "buyukluk_tutarliligi": {{"tutarli_mi": true/false, "aciklama": "..."}},
  "zamanlama_makul_mu": {{"makul_mu": true/false, "aciklama": "..."}},
  "kalabalik_ticaret_mi": {{"evet_mi": true/false, "kanit": "..."}},
  "gecersiz_kilma_kosulu": {{
     "kosul": "tek, somut, izlenebilir koşul",
     "izleme_yontemi": "fiyat_seviyesi|haber_anahtar_kelime|veri_aciklamasi",
     "zayif_sinyal_kelimeleri": ["3-5 adet zayıf çelişki kelimesi/ifadesi"]
  }},
  "redteam_guven": "dusuk|orta|yuksek",
  "guven_dusurme_gerekcesi": "... veya null"
}}
NOT: "redteam_guven" = tüm cevaplarını birlikte tartarak TEZİN hak ettiği güven
(kendi eleştirine duyduğun güven DEĞİL)."""


KURTARMA_PROMPT = """Sen temkinli bir risk yöneticisisin. Açık bir yatırım tezi zayıflama şüphesine düştü.
Görevin üç sonuçtan birine karar vermek — tezi tamamen terk etmek ile hiçbir şey yapmamak arasında
orta yol (kısmi çıkış) da bir seçenek.

TEZ: {symbol} ({market}), yön: {direction}
ZİNCİR: {chain}
GİRİŞ REFERANS FİYATI: {entry} | GÜNCEL FİYAT: {price} | STOP SEVİYESİ: {stop}
HEDEF: %{low}-{high} | GEÇEN SÜRE: {elapsed} gün / ufuk {horizon_days} gün
TETİKLENEN SİNYALLER: {signals}

GÜNCEL TEKNİK GÖRÜNÜM:
{teknik}

KURALLAR:
- "yanlis_alarm": tez hâlâ sağlam, sinyaller gürültü (özellikle sadece zaman sinyali varsa mekanizma
  yavaş işliyor olabilir)
- "kismi_cikis": tez zayıfladı ama ölmedi — riski azalt, cikis_orani belirle (0.3 hafif / 0.5 orta / 0.7 ciddi)
- "tam_cikis": tezin ana mekanizması bozuldu
SADECE geçerli JSON döndür:
{{"karar": "yanlis_alarm|kismi_cikis|tam_cikis", "gerekce": "1-2 cümle", "cikis_orani": 0.3|0.5|0.7|null}}"""


IKINCI_DERECE_PROMPT = """Sen kıdemli bir makro/sektör analistisin. Aşağıdaki haberler
bizim doğrudan anahtar kelime eşleştirmemizle (ticker adı geçmiyor, tema kelimesi yok)
izlediğimiz hiçbir sembole bağlanamadı — ama birden fazla bağımsız kaynakta çıktı,
yani muhtemelen önemli bir haber.

Görevin: bu haberlerin, aşağıdaki DAR evrenimizi DOLAYLI (ikinci derece) bir
mekanizmayla etkileyip etkilemediğini değerlendirmek — tedarik zinciri, girdi
maliyeti, rakip/ikame etkisi, düzenleyici emsal, sektörel yayılma gibi somut
zincirler. Sadece GERÇEKÇİ ve SOMUT bir mekanizma kurabildiğin haber-sembol
çiftini listele; "muhtemelen ilgilidir" gibi belirsiz bağ YETERSİZ, halüsinasyon
yapma. Emin değilsen o haberi atla.

İZLENEN EVREN (SADECE bu listeden sembol seç, başka ticker UYDURMA):
{evren}

HABERLER:
{haberler}

SADECE geçerli JSON döndür:
{{"baglar": [{{"haber_no": 1, "sembol": "XOM", "yon": "yukselis|dusus",
"mekanizma": "1-2 cümle somut zincir", "guven": "dusuk|orta|yuksek"}}]}}
Hiçbir somut bağ yoksa: {{"baglar": []}}"""


def ikinci_derece(clusters):
    """Faz 12 B: eşleşmeyen+çok-kaynaklı kümelerden ikinci derece (dolaylı)
    bağ arar. TEK toplu çağrı (kota-cimri, D'deki triage ile aynı desen).
    Evren KAPALI liste olarak verilir (halüsinasyon savunması — plan bölüm B).
    Hata/boş sonuçta sessizce [] döner (fail-safe, ana akış durmaz)."""
    if not clusters:
        return []
    from config import CORE_SYMBOLS
    evren = ", ".join(f'{s} ({i["name"]}, {"/".join(i["themes"])})' for s, i in CORE_SYMBOLS.items())
    haberler = "\n".join(
        f'{i + 1}. {c["rep"]["title"][:160]}' for i, c in enumerate(clusters))
    try:
        data = _parse_json(_call(
            IKINCI_DERECE_PROMPT.format(evren=evren, haberler=haberler),
            call_type="ikinci_derece"))
        return data.get("baglar", [])
    except Exception as e:
        print(f"  ikinci derece hatası (atlanıyor): {str(e)[:80]}")
        return []


def kurtarma_degerlendir(thesis, price, entry, stop, low, high, elapsed, horizon_days, signals,
                         teknik="veri alınamadı"):
    draft = thesis["draft_chain"]
    prompt = KURTARMA_PROMPT.format(
        symbol=thesis["symbol"], market=thesis["market"], direction=thesis["direction"],
        chain=json.dumps(draft.get("zincir", []), ensure_ascii=False),
        entry=entry, price=price, stop=stop, low=low, high=high,
        elapsed=elapsed, horizon_days=horizon_days,
        signals=", ".join(signals), teknik=teknik,
    )
    return _parse_json(_call(prompt, call_type="kurtarma"))


def triage(events):
    """Toplu ön eleme (tez kalitesi fazı): tek Gemini çağrısıyla rutin/geriye
    dönük/dolaylı haberleri ele. Hata olursa fail-open — hepsi geçer (nöbet durmaz).
    Dönüş: (geçen_olaylar, elenen_sayısı)."""
    if not events:
        return [], 0
    listing = "\n".join(
        f'{i + 1}. [{e["symbol"]} / {e["category"]}] {e["title"][:140]}'
        for i, e in enumerate(events))
    try:
        verdicts = _parse_json(_call(TRIAGE_PROMPT.format(events=listing), call_type="triage"))
        rejected = {v["no"] for v in verdicts if not v.get("gecer", True)}
        for v in verdicts:
            if not v.get("gecer", True) and 1 <= v["no"] <= len(events):
                e = events[v["no"] - 1]
                print(f'  triage eledi: [{e["symbol"]}] {v.get("neden", "")}')
                storage.insert_triaj_denemesi(e["symbol"], e.get("url"), "triaj_eledi", v.get("neden"))
        passed = [e for i, e in enumerate(events) if (i + 1) not in rejected]
        return passed, len(events) - len(passed)
    except Exception as e:
        print(f"  triage hatası (hepsi geçiriliyor): {str(e)[:80]}")
        return events, 0


def _snapshot_text(snapshot):
    if isinstance(snapshot, str):  # analytics.prompt_blok hazır metni (faz 11)
        return snapshot
    if not snapshot:
        return "veri alınamadı"
    parts = []
    if snapshot.get("price") is not None:
        parts.append(f'güncel fiyat {snapshot["price"]}')
    if snapshot.get("chg_1m_pct") is not None:
        parts.append(f'son 1 ay %{snapshot["chg_1m_pct"]:+.1f}')
    if snapshot.get("pct_from_52w_high") is not None:
        parts.append(f'52 hafta zirvesinin %{snapshot["pct_from_52w_high"]:.1f} altında')
    if snapshot.get("volume_z") is not None:
        parts.append(f'hacim z-skoru {snapshot["volume_z"]:+.1f}')
    return ", ".join(parts) or "veri alınamadı"


MIN_ETKI_PCT_US = 0.5  # bkz. MIN_ETKI_NOTU

MIN_ETKI_NOTU = """23 Temmuz 2026: sabit %2 eşiği kendi kanıtlı BIST kurulumlarımızın
(taban_kirilimi %1.75, sikisma_kirilim_adayi %1.59) getirisinden bile yüksekti.
BIST'te tamamen kaldırıldı (engel_kontrol zaten enflasyon/mevduat kıyasıyla
doğal bir fren uyguluyor). ABD'de engel_kontrol hiç bloklamıyor (Ayarlar'da
sadece TL enflasyon/mevduat alanı var, USD risksiz oranı tanımlı değil) — o
yüzden ABD'de gürültü-seviyesi bir taban (%0.5) bırakıldı."""


def _buyukluk_kural(market):
    if market == "BIST":
        return "Aşırı küçük/anlamsız bir etki bekliyorsan bunu düşük güvenle işaretle."
    return (f'Beklenen etki %{MIN_ETKI_PCT_US:g}\'ten küçükse bu bir tez değildir — '
            '{"tez_yok": true, "neden": "etki çok küçük"} döndür.')


def draft_chain(event, snapshot=None):
    from config import SYMBOLS
    prompt = DRAFT_PROMPT.format(
        title=event["title"], summary=event["summary"][:400],
        symbol=event["symbol"], name=SYMBOLS[event["symbol"]]["name"],
        market=event["market"], category=event["category"],
        source_count=event["source_count"], snapshot=_snapshot_text(snapshot),
        buyukluk_kural=_buyukluk_kural(event["market"]),
    )
    return _parse_json(_call(prompt, call_type="taslak"))


def red_team(event, draft, snapshot=None):
    prompt = REDTEAM_PROMPT.format(
        title=event["title"], symbol=event["symbol"], market=event["market"],
        chain=json.dumps(draft["zincir"], ensure_ascii=False),
        direction=draft["yon"],
        low=draft["buyukluk_araligi_pct"][0], ust=draft["buyukluk_araligi_pct"][1],
        horizon=f'{draft.get("ufuk_deger", "?")} {draft["ufuk"]}',
        snapshot=_snapshot_text(snapshot),
    )
    return _parse_json(_call(prompt, call_type="redteam"))


def merge(event, draft, redteam):
    """Birleştirme — saf kod, AI yok (plan 5.3).

    Dönüş: (final_confidence, tier, status, neden). Tez kalitesi kuralları:
    - önemlilik=hayır -> tez açılmaz (iptal, nedeni kayıtlı)
    - fiyatlanmış=evet -> güven 1 basamak düşer (23 Temmuz 2026: eskiden ayrıca
      koşulsuz iptal de ediyordu — aynı sinyali çifte cezalandırıyordu, en
      güvenilir adayı bile otomatik öldürüyordu. Artık tek ceza güven zincirine
      işleniyor, geri kalanı final==düşük kontrolü belirliyor)
    - hedef üst < eşik -> tez değil (iptal); eşik BIST'te 0 (engel_kontrol zaten
      aşağıda çalışıyor), ABD'de %0.5 (bkz. MIN_ETKI_NOTU)
    - final=düşük -> 'taslak': kayıt durur ama takip edilmez, karneye girmez
    """
    level = min(_ORDER.get(draft.get("taslak_guven", "dusuk"), 0),
                _ORDER.get(redteam.get("redteam_guven", "dusuk"), 0))

    taban = (redteam.get("taban_orani") or {}).get("basari_orani_pct")
    if taban is not None and taban < 40:
        level -= 1
    fiyatlanmis = (redteam.get("zaten_fiyatlanmis_mi") or {}).get("cevap") == "evet"
    if fiyatlanmis:
        level -= 1
    level = max(level, 0)
    final = ["dusuk", "orta", "yuksek"][level]

    onemlilik = redteam.get("onemlilik") or {}
    if onemlilik.get("onemli_mi") is False:
        return final, "gozlem", "iptal_edildi", f'red-team: olay önemsiz — {onemlilik.get("aciklama", "")[:150]}'

    try:
        ust = abs(float(draft["buyukluk_araligi_pct"][1]))
    except (TypeError, ValueError, IndexError, KeyError):
        ust = 0.0
    esik = 0.0 if event["market"] == "BIST" else MIN_ETKI_PCT_US
    if ust < esik:
        return final, "gozlem", "iptal_edildi", f"hedef aralığı anlamsız (üst %{ust:g} < %{esik:g})"

    kosul = ((redteam.get("gecersiz_kilma_kosulu") or {}).get("kosul") or "").strip()
    if len(kosul) < 10:  # belirsiz geçersiz kılma koşulu: yayınlanmaz (v1'de retry yok)
        return final, "gozlem", "iptal_edildi", "geçersiz kılma koşulu belirsiz"

    if final == "dusuk":
        # Düşük güven = tez değil, kayıtlı gözlem. Takip ve karne dışı (kullanıcı
        # kararı: "tezler bu kadar yoğun ve anlamsız olmamalı").
        return final, "gozlem", "taslak", "düşük güven — takip edilmiyor"

    if final == "yuksek" and event["category"] in ("jeopolitik", "makro"):
        tier = "kritik"
    else:
        tier = "orta"
    return final, tier, "acik", None
