"""Finansal beyin: taslak zincir -> kendini eleştiri (red-team) -> birleştirme (kod).

Plan bölüm 5. v1'de function-calling araçları yok (faz 6'da eklenecek);
red-team bu yüzden taban oranına "veri yok" der — halüsinasyon kuralı gereği.
"""
import json
import os
import time

from google import genai

from config import GEMINI_THROTTLE_SECONDS

_ORDER = {"dusuk": 0, "orta": 1, "yuksek": 2}
_client = None
_last_call = 0.0


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def _call(prompt):
    """Throttle'lı Gemini çağrısı; geçici hatalarda (429/503) 2 kez yeniden dener."""
    global _last_call
    last_err = None
    for attempt in range(3):
        wait = GEMINI_THROTTLE_SECONDS - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        try:
            resp = _get_client().models.generate_content(
                model=os.environ.get("GEMINI_MODEL", "gemini-flash-latest"),
                contents=prompt,
            )
            _last_call = time.time()
            return resp.text
        except Exception as e:
            _last_call = time.time()
            last_err = e
            if any(code in str(e) for code in ("429", "503")) and attempt < 2:
                time.sleep(15 * (attempt + 1))  # geçici yoğunluk: bekle ve tekrar dene
                continue
            raise
    raise last_err


def _parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


DRAFT_PROMPT = """Sen deneyimli bir finansal analistsin. Aşağıdaki haber olayı için sebep-sonuç zinciri kur.

OLAY:
Başlık: {title}
Özet: {summary}
İlgili sembol: {symbol} ({name}, {market})
Kategori: {category}
Kaç bağımsız kaynak verdi: {source_count}

KURALLAR:
- Her zincir adımı tek bir mekanizma anlatır ve kendi güven seviyesini taşır.
- Güven değerleri SADECE şunlar olabilir: "dusuk", "orta", "yuksek".
- Toplam güven zincirin EN ZAYIF halkasına göre belirlenir, ortalamaya göre değil.
- Emin olmadığın şeyi yüksek güvenle işaretleme. Abartılı hedef verme; {market} piyasasında
  bu tür olaylar için gerçekçi büyüklük aralığı kullan.
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

8 SORUYU SIRAYLA CEVAPLA. Elinde veri olmayan soruda dürüstçe "veri yok" yaz — SAYI UYDURMA.
Güven değerleri SADECE: "dusuk", "orta", "yuksek". SADECE geçerli JSON döndür.

JSON ŞEMASI:
{{
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
}}"""


KURTARMA_PROMPT = """Sen temkinli bir risk yöneticisisin. Açık bir yatırım tezi zayıflama şüphesine düştü.
Görevin üç sonuçtan birine karar vermek — tezi tamamen terk etmek ile hiçbir şey yapmamak arasında
orta yol (kısmi çıkış) da bir seçenek.

TEZ: {symbol} ({market}), yön: {direction}
ZİNCİR: {chain}
GİRİŞ REFERANS FİYATI: {entry} | GÜNCEL FİYAT: {price} | STOP SEVİYESİ: {stop}
HEDEF: %{low}-{high} | GEÇEN SÜRE: {elapsed} gün / ufuk {horizon_days} gün
TETİKLENEN SİNYALLER: {signals}

KURALLAR:
- "yanlis_alarm": tez hâlâ sağlam, sinyaller gürültü (özellikle sadece zaman sinyali varsa mekanizma
  yavaş işliyor olabilir)
- "kismi_cikis": tez zayıfladı ama ölmedi — riski azalt, cikis_orani belirle (0.3 hafif / 0.5 orta / 0.7 ciddi)
- "tam_cikis": tezin ana mekanizması bozuldu
SADECE geçerli JSON döndür:
{{"karar": "yanlis_alarm|kismi_cikis|tam_cikis", "gerekce": "1-2 cümle", "cikis_orani": 0.3|0.5|0.7|null}}"""


def kurtarma_degerlendir(thesis, price, entry, stop, low, high, elapsed, horizon_days, signals):
    draft = thesis["draft_chain"]
    prompt = KURTARMA_PROMPT.format(
        symbol=thesis["symbol"], market=thesis["market"], direction=thesis["direction"],
        chain=json.dumps(draft.get("zincir", []), ensure_ascii=False),
        entry=entry, price=price, stop=stop, low=low, high=high,
        elapsed=elapsed, horizon_days=horizon_days,
        signals=", ".join(signals),
    )
    return _parse_json(_call(prompt))


def draft_chain(event):
    from config import SYMBOLS
    prompt = DRAFT_PROMPT.format(
        title=event["title"], summary=event["summary"][:400],
        symbol=event["symbol"], name=SYMBOLS[event["symbol"]]["name"],
        market=event["market"], category=event["category"],
        source_count=event["source_count"],
    )
    return _parse_json(_call(prompt))


def red_team(event, draft):
    prompt = REDTEAM_PROMPT.format(
        title=event["title"], symbol=event["symbol"], market=event["market"],
        chain=json.dumps(draft["zincir"], ensure_ascii=False),
        direction=draft["yon"],
        low=draft["buyukluk_araligi_pct"][0], ust=draft["buyukluk_araligi_pct"][1],
        horizon=f'{draft.get("ufuk_deger", "?")} {draft["ufuk"]}',
    )
    return _parse_json(_call(prompt))


def merge(event, draft, redteam):
    """Birleştirme — saf kod, AI yok (plan 5.3). Dönüş: (final_confidence, tier, status)."""
    level = min(_ORDER.get(draft.get("taslak_guven", "dusuk"), 0),
                _ORDER.get(redteam.get("redteam_guven", "dusuk"), 0))

    taban = (redteam.get("taban_orani") or {}).get("basari_orani_pct")
    if taban is not None and taban < 40:
        level -= 1
    if (redteam.get("zaten_fiyatlanmis_mi") or {}).get("cevap") == "evet":
        level -= 1
    level = max(level, 0)
    final = ["dusuk", "orta", "yuksek"][level]

    kosul = ((redteam.get("gecersiz_kilma_kosulu") or {}).get("kosul") or "").strip()
    if len(kosul) < 10:  # belirsiz geçersiz kılma koşulu: yayınlanmaz (v1'de retry yok)
        return final, "gozlem", "iptal_edildi"

    if final == "yuksek" and event["category"] in ("jeopolitik", "makro"):
        tier = "kritik"
    elif final in ("yuksek", "orta"):
        tier = "orta"
    else:
        tier = "gozlem"
    return final, tier, "acik"
