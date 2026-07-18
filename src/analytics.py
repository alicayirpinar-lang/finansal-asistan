"""Analitik motor (faz 11) — deterministik veri analizi omurgası.

Felsefe: grafiği KOD okur (tekrarlanabilir, test edilebilir), AI en son adımda
yapılandırılmış çıktıyı yorumlar. AI hiçbir sayı/seviye üretmez.

Katmanlar:
- gösterge vektörü: trend, momentum, oynaklık/sıkışma, seviyeler, hacim
  karakteri, görece güç, ADX, çoklu zaman dilimi (haftalık)
- kurulum tespiti: 4 adlandırılmış kurulum, sabit eşik, 0-100 skor + koşul listesi
- rejim: endeks MA200 + oynaklık -> risk_on / notr / risk_off
- olay günü tepkisi (PEAD dersi): habere İLK fiyat tepkisi sürüklenmenin yönüdür
- katalizör sınıflandırması: anahtar kelime kuralları (AI değil)
- engel oranı: tezin yıllık eşdeğeri enflasyon/mevduatı yenmiyorsa tez açılmaz

EŞİKLER DONMUŞTUR: backtest'e bakıp eşik oynamak p-hacking'dir
(literatür: canlı performans backtest'ten medyan %73 kötü — Bailey et al.).
Değişiklik ancak örneklem-dışı kanıtla ve tek seferde yapılır.
"""
import math

import pandas as pd
import yfinance as yf

from src.prices import yf_ticker, _clean

# --- Donmuş eşikler ---------------------------------------------------------
SIKISMA_PCTL = 20          # BB genişliği 1 yıllık persentil <= 20 -> sıkışma
KIRILIM_YAKIN_PCT = 3.0    # dirence <= %3 -> kırılım adayı
HACIM_ONAY_Z = 1.5
ADX_TREND_ESIK = 20
GERILME_ATR = 3.0          # MA20'den >= 3 ATR uzaklık -> aşırı gerilme
KURULUM_MIN_SKOR = 60      # bu skorun altı rapora/şeride girmez
BUYUK_FIRSAT_SKOR = 70
LIKIDITE_MIN = {"US": 2_000_000, "BIST": 50_000_000}   # 20g ort. işlem tutarı ($ / TL)

# KANIT KAPISI (tools/backtest_kurulum.py, 10 yıl, örneklem içi/dışı — 17.07.2026):
# Yalnızca HER İKİ dönemde de taban çizgisini yenen (pazar, kurulum) çiftleri
# "kanıtlı" sayılır ve büyük fırsat şeridini tetikleyebilir. Diğerleri veri
# olarak saklanır/prompta bağlam olarak gider ama iddia taşımaz.
# Bulgular: BIST taban_kirilimi (out %1.75 vs taban %0.81) ve BIST sıkışma
# (out %1.59 vs %0.81) kanıtlı; momentum_devam BIST out'ta NEGATİF; US'te
# hiçbir kurulum tabanı yenmedi; aşırı_gerilme tersine dönüş göstermiyor
# (aksine devam ediyor) -> risk iddiası kaldırıldı, bilgi notuna düşürüldü.
KANITLI_KURULUMLAR = {("BIST", "taban_kirilimi"), ("BIST", "sikisma_kirilim_adayi")}

ENDEKS = {"BIST": "XU100.IS", "US": "^GSPC"}

# Katalizör sınıflandırması (kural tabanlı, AI yok). "guclu" olanlar büyük
# fırsat şeridine aday olabilir; "rutin" hiçbir zaman olamaz.
KATALIZOR_KURALLARI = [
    ("birlesme_satinalma", True,  ["satın alma", "birleşme", "acquisition", "merger", "devral", "takeover", "buyout"]),
    ("ihale_sozlesme",     True,  ["ihale", "sözleşme imzala", "sipariş ald", "contract award", "order win", "anlaşma imzala"]),
    ("regulasyon_onay",    True,  ["fda", "onay ald", "ruhsat", "lisans ald", "approval", "yaptırım", "sanction", "dava sonuç"]),
    ("bilanco_surprizi",   True,  ["bilanço", "net kâr", "net kar", "earnings", "beats", "misses", "guidance", "kâr açıkla"]),
    ("arz_soku",           True,  ["üretim durdu", "kesinti", "grev", "supply disruption", "shortage", "kapasite", "production halt", "opec"]),
    ("faiz_makro",         False, ["faiz karar", "rate decision", "enflasyon", "inflation", "merkez bankası", "fed ", "tcmb"]),
]


def katalizor_tipi(text):
    """Dönüş: (tip, guclu_mu). Eşleşme yoksa ('genel', False)."""
    low = text.lower()
    for tip, guclu, kelimeler in KATALIZOR_KURALLARI:
        if any(k in low for k in kelimeler):
            return tip, guclu
    return "genel", False


# --- Gösterge yardımcıları ---------------------------------------------------

def _rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, float("nan"))
    return 100 - 100 / (1 + rs)


def _atr(df, n=14):
    h, l, c = df["High"], df["Low"], df["Close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def _adx(df, n=14):
    h, l = df["High"], df["Low"]
    up, dn = h.diff(), -l.diff()
    plus_dm = ((up > dn) & (up > 0)) * up
    minus_dm = ((dn > up) & (dn > 0)) * dn
    atr = _atr(df, n).replace(0, float("nan"))
    plus_di = 100 * plus_dm.ewm(alpha=1 / n, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / n, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, float("nan"))
    return dx.ewm(alpha=1 / n, adjust=False).mean()


def _bb_genislik(close, n=20):
    ma = close.rolling(n).mean()
    sd = close.rolling(n).std()
    return (4 * sd) / ma.replace(0, float("nan"))  # bant genişliği / fiyat


_endeks_cache = {}


def _endeks_df(market):
    if market not in _endeks_cache:
        try:
            _endeks_cache[market] = yf.Ticker(ENDEKS[market]).history(period="2y")
        except Exception:
            _endeks_cache[market] = None
    return _endeks_cache[market]


# --- Gösterge vektörü --------------------------------------------------------

def vektor(df, market=None):
    """Tek sembolün OHLCV geçmişinden gösterge vektörü. df: >= 200 satır günlük."""
    df = df.dropna(subset=["Close", "High", "Low", "Volume"])
    if len(df) < 60:
        return None
    c, v = df["Close"], df["Volume"]
    price = float(c.iloc[-1])

    ma20, ma50, ma200 = (c.rolling(n).mean() for n in (20, 50, 200))
    atr = _atr(df)
    atr_son = float(atr.iloc[-1]) if not math.isnan(atr.iloc[-1]) else None

    # Seviyeler: son 120 günün pivotları (basit swing: 10g pencere uçları hariç yerel uç)
    win = c.tail(120)
    direnc = float(win.rolling(10, center=True).max().dropna().max())
    destek = float(win.rolling(10, center=True).min().dropna().min())

    # Hacim karakteri
    ret = c.pct_change()
    up_vol = float(v.tail(20)[ret.tail(20) > 0].sum())
    dn_vol = float(v.tail(20)[ret.tail(20) < 0].sum())
    obv = (v * ret.apply(lambda r: 1 if r > 0 else (-1 if r < 0 else 0))).cumsum()
    vol_mean, vol_std = v.rolling(20).mean().iloc[-1], v.rolling(20).std().iloc[-1]

    # Sıkışma: BB genişliğinin 1 yıllık persentil konumu
    bbw = _bb_genislik(c).dropna()
    sikisma_pctl = float((bbw.tail(252) <= bbw.iloc[-1]).mean() * 100) if len(bbw) > 60 else None

    # Haftalık trend (çoklu zaman dilimi)
    haftalik = c.resample("W").last().dropna()
    h_ma10 = haftalik.rolling(10).mean()
    haftalik_trend = None
    if len(h_ma10.dropna()) >= 2:
        haftalik_trend = "yukari" if (haftalik.iloc[-1] > h_ma10.iloc[-1]
                                      and h_ma10.iloc[-1] >= h_ma10.iloc[-2]) else (
            "asagi" if haftalik.iloc[-1] < h_ma10.iloc[-1] else "yatay")

    # Görece güç: 3 aylık getiri - endeks 3 aylık getirisi
    rs_3ay = None
    if market:
        edf = _endeks_df(market)
        if edf is not None and len(edf) > 70 and len(c) > 66:
            sym_r = c.iloc[-1] / c.iloc[-66] - 1
            idx_r = edf["Close"].iloc[-1] / edf["Close"].iloc[-66] - 1
            rs_3ay = _clean((sym_r - idx_r) * 100, 1)

    adx = _adx(df)
    hi52 = float(c.tail(252).max())

    return {
        "fiyat": _clean(price, 2),
        "ma20": _clean(ma20.iloc[-1], 2), "ma50": _clean(ma50.iloc[-1], 2),
        "ma200": _clean(ma200.iloc[-1], 2),
        "trend_dizilim": "yukari" if (price > (ma50.iloc[-1] or price) > (ma200.iloc[-1] or price))
                         else ("asagi" if price < (ma50.iloc[-1] or price) < (ma200.iloc[-1] or price) else "karisik"),
        "haftalik_trend": haftalik_trend,
        "rsi": _clean(_rsi(c).iloc[-1], 1),
        "adx": _clean(adx.iloc[-1], 1),
        "atr_pct": _clean(atr_son / price * 100, 2) if atr_son else None,
        "sikisma_pctl": _clean(sikisma_pctl, 0),
        "direnc": _clean(direnc, 2), "destek": _clean(destek, 2),
        "dirence_pct": _clean((direnc - price) / price * 100, 1),
        "hi52_pct": _clean((hi52 - price) / hi52 * 100, 1),
        "chg_1ay_pct": _clean((price / float(c.iloc[-22]) - 1) * 100, 1) if len(c) > 22 else None,
        "hacim_z": _clean((v.iloc[-1] - vol_mean) / vol_std, 1) if vol_std else None,
        "up_down_hacim": _clean(up_vol / dn_vol, 2) if dn_vol else None,
        "obv_egim": "yukari" if len(obv) > 20 and obv.iloc[-1] > obv.iloc[-20] else "asagi",
        "rs_3ay_pct": rs_3ay,
        "gerilme_atr": _clean(abs(price - ma20.iloc[-1]) / atr_son, 1)
                       if atr_son and not math.isnan(ma20.iloc[-1]) else None,
        "islem_tutari_20g": _clean(float((v * c).rolling(20).mean().iloc[-1]), 0),
    }


# --- Kurulum tespiti ---------------------------------------------------------

def kurulumlar(vec, market):
    """4 adlandırılmış kurulum. Dönüş: [{ad, yon, skor, kosullar}] — skor >= esikte."""
    if not vec:
        return []
    out = []

    def _ekle(ad, yon, kosullar, taban):
        skor = min(100, taban + 10 * len(kosullar))
        if skor >= KURULUM_MIN_SKOR:
            out.append({"ad": ad, "yon": yon, "skor": skor, "kosullar": kosullar,
                        "kanitli": (market, ad) in KANITLI_KURULUMLAR})

    sik = vec.get("sikisma_pctl")
    hz = vec.get("hacim_z") or 0

    # 1) Sıkışma kırılım adayı: yay gerilmiş + dirence yakın + para giriyor
    if sik is not None and sik <= SIKISMA_PCTL and (vec.get("dirence_pct") or 99) <= KIRILIM_YAKIN_PCT:
        k = [f"oynaklık sıkışması (pctl {sik:g})", f'dirence %{vec["dirence_pct"]:g}']
        if vec.get("obv_egim") == "yukari":
            k.append("OBV yukarı (birikim izi)")
        if vec.get("haftalik_trend") == "yukari":
            k.append("haftalık trend uyumlu")
        if hz >= HACIM_ONAY_Z:
            k.append(f"hacim onayı (z={hz:g})")
        _ekle("sikisma_kirilim_adayi", "yukselis", k, 40)

    # 2) Taban kırılımı: 52h zirveye çok yakın + hacim + trend
    if (vec.get("hi52_pct") or 99) <= 2.0 and hz >= HACIM_ONAY_Z:
        k = [f'52h zirveye %{vec["hi52_pct"]:g}', f"hacim onayı (z={hz:g})"]
        if vec.get("trend_dizilim") == "yukari":
            k.append("MA dizilimi yukarı")
        if (vec.get("rs_3ay_pct") or -99) > 0:
            k.append(f'endeksten güçlü (+%{vec["rs_3ay_pct"]:g})')
        _ekle("taban_kirilimi", "yukselis", k, 45)

    # 3) Momentum devam: dizilim yukarı + endeksten güçlü + MA20'ye sağlıklı geri çekilme
    if vec.get("trend_dizilim") == "yukari" and (vec.get("rs_3ay_pct") or -99) > 0 \
            and (vec.get("gerilme_atr") or 9) <= 1.0 and (vec.get("adx") or 0) >= ADX_TREND_ESIK:
        k = ["MA dizilimi yukarı", f'endeksten güçlü (+%{vec["rs_3ay_pct"]:g})',
             "MA20'ye sağlıklı geri çekilme", f'trend gücü ADX {vec["adx"]:g}']
        if vec.get("haftalik_trend") == "yukari":
            k.append("haftalık trend uyumlu")
        _ekle("momentum_devam", "yukselis", k, 40)

    # 4) Aşırı gerilme — BİLGİ notu. Backtest bulgusu: gerilen hisse tarihsel
    # olarak tersine DÖNMÜYOR (devam eğilimi baskın) — bu yüzden risk/yön
    # iddiası taşımaz, sadece "fiyat ortalamadan çok uzak" bilgisi verir.
    if (vec.get("gerilme_atr") or 0) >= GERILME_ATR or (vec.get("rsi") or 50) >= 80 \
            or (vec.get("rsi") or 50) <= 20:
        k = []
        if (vec.get("gerilme_atr") or 0) >= GERILME_ATR:
            k.append(f'MA20\'den {vec["gerilme_atr"]:g} ATR uzak')
        rsi = vec.get("rsi")
        if rsi is not None and (rsi >= 80 or rsi <= 20):
            k.append(f"RSI aşırı ({rsi:g})")
        k.append("not: tarihsel veri tersine dönüş göstermiyor (devam eğilimi baskın)")
        _ekle("asiri_gerilme", "bilgi", k, 50)

    return out


def likidite_ok(vec, market):
    esik = LIKIDITE_MIN.get(market, 0)
    tutar = vec.get("islem_tutari_20g") if vec else None
    return (tutar or 0) >= esik, tutar


# --- Rejim, olay tepkisi, engel oranı ---------------------------------------

def rejim(market):
    """Deniz durumu: endeks MA200 üstü mü + oynaklık nerede."""
    try:
        edf = _endeks_df(market)
        c = edf["Close"].dropna()
        ma200 = c.rolling(200).mean().iloc[-1]
        ustu = bool(c.iloc[-1] > ma200)
        vol = c.pct_change().rolling(20).std() * (252 ** 0.5) * 100
        vol_pctl = float((vol.dropna().tail(252) <= vol.iloc[-1]).mean() * 100)
        durum = "risk_on" if ustu and vol_pctl < 70 else (
            "risk_off" if (not ustu and vol_pctl >= 70) else "notr")
        return {"rejim": durum, "ma200_ustu": ustu, "oynaklik_pctl": round(vol_pctl)}
    except Exception:
        return {"rejim": "bilinmiyor", "ma200_ustu": None, "oynaklik_pctl": None}


def olay_tepkisi(df):
    """PEAD dersi: habere İLK fiyat tepkisi. Son barın getirisi + hacim katı."""
    try:
        c, v = df["Close"].dropna(), df["Volume"].dropna()
        getiri = _clean((c.iloc[-1] / c.iloc[-2] - 1) * 100, 2)
        kat = _clean(v.iloc[-1] / v.tail(21).iloc[:-1].mean(), 1)
        return {"gun_getiri_pct": getiri, "hacim_kati": kat}
    except Exception:
        return None


_UFUK_GUN = {"gun": 1, "hafta": 7, "ay": 30}


def yillik_esdeger(hedef_pct, ufuk, ufuk_deger):
    """'2 ayda %5' -> yıllık bileşik eşdeğeri (~%34)."""
    try:
        gun = max(int(float(ufuk_deger or 1)) * _UFUK_GUN.get(ufuk, 30), 5)
        return _clean(((1 + float(hedef_pct) / 100) ** (365.0 / gun) - 1) * 100, 1)
    except (TypeError, ValueError):
        return None


def engel_kontrol(draft, market, settings):
    """Tezin yıllık eşdeğeri risksiz alternatifi yenmiyorsa tez açılmaz.
    BIST: TL bazlı -> enflasyon/mevduat kıyası. US: dolar bazlı, sadece bilgi notu."""
    try:
        low, high = draft["buyukluk_araligi_pct"]
        orta = (abs(float(low)) + abs(float(high))) / 2
    except (TypeError, ValueError, KeyError):
        return {"gecemedi": False, "metin": ""}
    yillik = yillik_esdeger(orta, draft.get("ufuk"), draft.get("ufuk_deger"))
    if yillik is None:
        return {"gecemedi": False, "metin": ""}
    enf = (settings or {}).get("enflasyon_yillik")
    mev = (settings or {}).get("mevduat_yillik")
    if market != "BIST" or (enf is None and mev is None):
        return {"gecemedi": False,
                "metin": f"Yıllık eşdeğer: ~%{yillik:g} (dolar bazlı)" if market == "US"
                else f"Yıllık eşdeğer: ~%{yillik:g}"}
    engel = max(x for x in (enf, mev) if x is not None)
    kaynak = "mevduat" if (mev is not None and mev >= (enf or 0)) else "enflasyon"
    if yillik < float(engel):
        return {"gecemedi": True,
                "neden": f"yıllık eşdeğer %{yillik:g} < {kaynak} %{engel:g} — risksiz alternatif daha iyi",
                "metin": f"Yıllık eşdeğer: ~%{yillik:g} — {kaynak} (%{engel:g}) ALTINDA ✗"}
    return {"gecemedi": False,
            "metin": f"Yıllık eşdeğer: ~%{yillik:g} — {kaynak} (%{engel:g}) üstünde ✓"}


# --- Tam analiz + AI için yapılandırılmış blok --------------------------------

def sembol_analiz(symbol, market):
    """Bir sembolün tam analizi (2 yıl günlük veri, tek indirme)."""
    try:
        df = yf.Ticker(yf_ticker(symbol, market)).history(period="2y")
    except Exception:
        return None
    vec = vektor(df, market)
    if not vec:
        return None
    setups = kurulumlar(vec, market)
    lik_ok, tutar = likidite_ok(vec, market)
    return {"vektor": vec, "kurulumlar": setups, "likidite_ok": lik_ok,
            "tepki": olay_tepkisi(df)}


def prompt_blok(analiz, rejim_bilgi):
    """AI'ya giden yapılandırılmış teknik özet — AI bunu YORUMLAR, üretmez."""
    if not analiz:
        return "teknik veri alınamadı"
    v = analiz["vektor"]
    satirlar = [
        f'Fiyat {v["fiyat"]}, trend: {v["trend_dizilim"]} (haftalık: {v["haftalik_trend"]}), '
        f'RSI {v["rsi"]}, ADX {v["adx"]}, son 1 ay %{v["chg_1ay_pct"]:+g}' if v.get("chg_1ay_pct") is not None else "",
        f'Seviyeler: destek {v["destek"]} / direnç {v["direnc"]} (dirence %{v["dirence_pct"]:g}), '
        f'52h zirveye %{v["hi52_pct"]:g}',
        f'Hacim: z={v["hacim_z"]}, alış/satış hacim oranı {v["up_down_hacim"]}, OBV {v["obv_egim"]}, '
        f'endekse görece 3 ay {"+%" + str(v["rs_3ay_pct"]) if (v.get("rs_3ay_pct") or 0) >= 0 else "%" + str(v["rs_3ay_pct"])}',
        f'Sıkışma persentili: {v["sikisma_pctl"]} (düşük=yay gerilmiş)',
    ]
    for s in analiz["kurulumlar"]:
        etiket = "backtest kanıtlı" if s.get("kanitli") else "kanıt yok — bağlamsal bilgi"
        satirlar.append(f'KURULUM: {s["ad"]} (yön: {s["yon"]}, skor {s["skor"]}, {etiket}) — '
                        + "; ".join(s["kosullar"]))
    if not analiz["kurulumlar"]:
        satirlar.append("KURULUM: yok (nötr grafik)")
    if analiz.get("tepki"):
        t = analiz["tepki"]
        satirlar.append(f'OLAY GÜNÜ TEPKİSİ: fiyat %{t["gun_getiri_pct"]:+g}, '
                        f'hacim normalin {t["hacim_kati"]} katı')
    if not analiz.get("likidite_ok", True):
        satirlar.append("UYARI: likidite düşük — pozisyona girilmesi zor olabilir")
    satirlar.append(f'PİYASA REJİMİ: {rejim_bilgi.get("rejim")} '
                    f'(endeks MA200 {"üstünde" if rejim_bilgi.get("ma200_ustu") else "altında"}, '
                    f'oynaklık pctl {rejim_bilgi.get("oynaklik_pctl")})')
    return "\n".join(s for s in satirlar if s)


def buyuk_firsat_mu(katalizor_guclu, analiz, rejim_bilgi, yon):
    """Büyük fırsat şeridi kararı — SAF KOD: güçlü katalizör + güçlü kurulum
    (yön uyumlu) + rejim karşı rüzgarı yok."""
    if not (katalizor_guclu and analiz):
        return False
    # Yalnızca kanıt kapısından geçmiş kurulumlar şeridi tetikleyebilir
    uyumlu = [s for s in analiz["kurulumlar"]
              if s.get("kanitli") and s["skor"] >= BUYUK_FIRSAT_SKOR
              and yon == "yukselis" and s["yon"] == "yukselis"]
    if not uyumlu:
        return False
    r = rejim_bilgi.get("rejim")
    if yon == "yukselis" and r == "risk_off":
        return False
    if yon == "dusus" and r == "risk_on":
        return False
    return True
