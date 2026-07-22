"""Tez takibi (plan bölüm 7): açık tezlerin günlük kontrolü.

Kontrol sırası (öncelik): stop ihlali > hedef aşıldı > hedefe yaklaşıldı >
süre doldu > zayıflama şüphesi (≥2 sinyal → kurtarma değerlendirmesi).
Bildirimler alerts tablosuyla teklenir — aynı tez için aynı uyarı bir kez gider.
"""
import os
import re
from datetime import datetime, timezone

from src import brain, notifier, prices, storage

_UFUK_GUN = {"gun": 1, "hafta": 7, "ay": 30}


def _parse_range(numrange_str):
    m = re.match(r"[\[\(]\s*([\d.]+)\s*,\s*([\d.]+)", str(numrange_str))
    return (float(m.group(1)), float(m.group(2))) if m else (10.0, 20.0)


def _horizon_days(draft):
    try:
        return max(1, int(float(draft.get("ufuk_deger", 1))) * _UFUK_GUN.get(draft.get("ufuk", "ay"), 30))
    except Exception:
        return 30


def _send_once(alert_type, thesis, text):
    if storage.alert_exists(alert_type, thesis["id"]):
        return False
    msg_id = notifier.send(text)
    storage.log_alert(alert_type, thesis["id"], msg_id, text.splitlines()[0])
    return True


def _bildir(sessiz, alert_type, thesis, text):
    """Sessiz modda (taslak/gözlem tezler — hiç önerilmedi) Telegram'a
    gitmez, sadece DB'ye yazılır (karne/takip geçmişi için)."""
    if sessiz:
        return False
    return _send_once(alert_type, thesis, text)


def check_thesis(thesis, gemini_cap, sessiz=False):
    tid, sym, market = thesis["id"], thesis["symbol"], thesis["market"]
    direction = thesis["direction"]
    sign = 1 if direction == "yukselis" else -1
    yon_txt = "yükseliş" if direction == "yukselis" else "düşüş"

    price = prices.current_price(sym, market)
    if price is None:
        storage.insert_thesis_check(tid, None, {}, "fiyat alınamadı")
        return f"{sym}: fiyat alınamadı"

    entry = thesis.get("entry_price_ref")
    inv = thesis.get("invalidation_condition") or {}
    stop = inv.get("stop_fiyat")

    # Referans fiyat yoksa geriye dönük ata (eski tezler için) ve izlemeye başla
    if not entry:
        atr = prices.atr14(sym, market)
        stop = round(price - sign * 2 * atr, 2) if atr else None
        inv["stop_fiyat"] = stop
        storage.update_thesis(tid, entry_price_ref=price, invalidation_condition=inv)
        storage.insert_thesis_check(tid, price, {"backfill": True}, "referans fiyat atandı")
        return f"{sym}: referans fiyat geriye dönük atandı ({price})"

    entry = float(entry)
    gain_pct = sign * (price - entry) / entry * 100
    low, high = _parse_range(thesis["target_range_pct"])
    draft = thesis["draft_chain"]
    horizon_days = _horizon_days(draft)
    created = datetime.fromisoformat(thesis["created_at"].replace("Z", "+00:00"))
    elapsed = (datetime.now(timezone.utc) - created).days

    snapshot = {"price": price, "entry": entry, "gain_pct": round(gain_pct, 2),
                "stop": stop, "elapsed_days": elapsed, "horizon_days": horizon_days}

    # 1) Stop ihlali → tez bozuldu (7/24 anlık — plan bölüm 9)
    if stop and sign * (price - float(stop)) < 0:
        storage.update_thesis(tid, status="tez_bozuldu", resolved_at="now()",
                              resolution_note=f"stop ihlali: fiyat {price}, stop {stop}",
                              expected_horizon_days=horizon_days)
        _bildir(sessiz, "tez_bozuldu", thesis,
                   f"🔴 TEZ BOZULDU: {sym} ({market})\n"
                   f"Fiyat {price} — stop seviyesi ({stop}) aşıldı.\n"
                   f"{yon_txt} tezi geçersiz. Pozisyonun varsa tam çıkışı değerlendir.\n"
                   f"Giriş referansı: {entry} | Değişim: %{gain_pct:.1f}")
        storage.insert_thesis_check(tid, price, snapshot, "tez_bozuldu")
        return f"{sym}: TEZ BOZULDU (stop ihlali)"

    # 2) Hedef üst sınırı aşıldı → hedefe ulaştı
    if gain_pct >= high:
        storage.update_thesis(tid, status="hedefe_ulasti", resolved_at="now()",
                              resolution_note=f"hedef aşıldı: %{gain_pct:.1f}",
                              expected_horizon_days=horizon_days)
        _bildir(sessiz, "hedef_asildi", thesis,
                   f"🎯 HEDEF AŞILDI: {sym} ({market})\n"
                   f"Kazanç %{gain_pct:.1f} — hedef bandın (%{low:.0f}-{high:.0f}) üstü.\n"
                   f"Kâr realizasyonu güçlü öneri. Karar senin.")
        storage.insert_thesis_check(tid, price, snapshot, "hedefe_ulasti")
        return f"{sym}: HEDEFE ULAŞTI (%{gain_pct:.1f})"

    # 3) Hedef alt sınırına yaklaşıldı (tez açık kalır, bir kez bildirilir)
    if gain_pct >= low:
        _bildir(sessiz, "hedef_yaklasti", thesis,
                   f"🟢 Hedefe yaklaşıldı: {sym} ({market})\n"
                   f"Kazanç %{gain_pct:.1f}, hedef bandı %{low:.0f}-{high:.0f}.\n"
                   f"Gözden geçir — kısmi kâr alımı değerlendirilebilir.")
        storage.insert_thesis_check(tid, price, snapshot, "hedef_yaklasti")
        return f"{sym}: hedefe yaklaşıldı (%{gain_pct:.1f})"

    # 4) Süre doldu (nötr — isabet karnesine girmez)
    if elapsed > horizon_days:
        storage.update_thesis(tid, status="suresi_doldu", resolved_at="now()",
                              resolution_note=f"{horizon_days} günlük ufuk doldu, sonuç: %{gain_pct:.1f}",
                              expected_horizon_days=horizon_days)
        _bildir(sessiz, "suresi_doldu", thesis,
                   f"⏳ Süresi doldu: {sym} ({market})\n"
                   f"{horizon_days} günlük ufuk geçti, ne hedef ne stop tetiklendi (%{gain_pct:.1f}).\n"
                   f"Tez sonuçsuz kapatıldı — karneye girmez.")
        storage.insert_thesis_check(tid, price, snapshot, "suresi_doldu")
        return f"{sym}: süresi doldu"

    # 5) Zayıflama şüphesi — sadece gerçek açık tezlerde (Gemini çağrısı içeriyor,
    # hiç önerilmemiş taslak/gözlem tezlere kota harcamaya değmez)
    if sessiz:
        storage.insert_thesis_check(tid, price, snapshot, "normal")
        return f"{sym}: normal (%{gain_pct:.1f}, gün {elapsed}/{horizon_days})"

    signals = []
    if stop:
        stop_dist = abs(entry - float(stop))
        adverse = -sign * (price - entry)
        if stop_dist > 0 and adverse >= 0.5 * stop_dist:
            signals.append("fiyat stop mesafesinin yarısını geçti")
    if elapsed >= horizon_days / 2 and gain_pct < low * 0.25:
        signals.append("ufkun yarısı geçti, beklenen yönde anlamlı hareket yok")

    if len(signals) >= 2 and not storage.kurtarma_exists_recent(tid):
        if storage.gemini_calls_today() + 1 > gemini_cap:
            result = "kurtarma gerekli ama Gemini tavanı dolu"
        else:
            try:
                verdict = brain.kurtarma_degerlendir(
                    thesis, price, entry, stop, low, high, elapsed, horizon_days, signals)
                karar = verdict.get("karar", "yanlis_alarm")
                oran = verdict.get("cikis_orani")
                storage.insert_kurtarma(tid, {"signals": signals, **snapshot}, karar, oran)
                if karar == "tam_cikis":
                    storage.update_thesis(tid, status="tez_bozuldu", resolved_at="now()",
                                          resolution_note=f"kurtarma: tam çıkış — {verdict.get('gerekce','')}")
                    _send_once("kurtarma_tam", thesis,
                               f"🔴 KURTARMA — TAM ÇIKIŞ: {sym} ({market})\n"
                               f"{verdict.get('gerekce', '')}\n"
                               f"Güncel: {price} (%{gain_pct:.1f}) | Stop: {stop}")
                elif karar == "kismi_cikis":
                    _send_once("kurtarma_kismi", thesis,
                               f"🟡 KURTARMA — KISMİ ÇIKIŞ ÖNERİSİ: {sym} ({market})\n"
                               f"Önerilen oran: %{int((oran or 0.5) * 100)}\n"
                               f"{verdict.get('gerekce', '')}\n"
                               f"Tez izlemede kalıyor. Karar senin.")
                result = f"kurtarma: {karar}"
            except Exception as e:
                result = f"kurtarma değerlendirmesi hata: {str(e)[:80]}"
        storage.insert_thesis_check(tid, price, {**snapshot, "signals": signals}, result)
        return f"{sym}: {result}"

    storage.insert_thesis_check(tid, price, snapshot, "normal")
    return f"{sym}: normal (%{gain_pct:.1f}, gün {elapsed}/{horizon_days})"


def run():
    cap = int(os.environ.get("DAILY_GEMINI_CAP", "40"))
    theses = storage.open_theses()
    print(f"{len(theses)} açık tez kontrol ediliyor...")
    for t in theses:
        try:
            print("  " + check_thesis(t, cap))
        except Exception as e:
            print(f'  ! {t["symbol"]}: hata — {str(e)[:120]} (devam ediliyor)')

    # Düşük güven/engel oranı yüzünden hiç açılmamış taslaklar — önceden
    # sonsuza kadar donuk kalıyor, karneye giremiyordu (21 Temmuz bulgusu:
    # TUPRS taslağı %10 kazandırmış ama sistem hiç bakmamıştı). Artık
    # sessizce (bildirimsiz) kontrol edilip bir sonuca bağlanıyorlar.
    taslaklar = storage.taslak_gozlem_theses()
    if taslaklar:
        print(f"{len(taslaklar)} taslak/gözlem tez sessizce kontrol ediliyor (karne için)...")
        for t in taslaklar:
            try:
                print("  " + check_thesis(t, cap, sessiz=True))
            except Exception as e:
                print(f'  ! {t["symbol"]}: hata — {str(e)[:120]} (devam ediliyor)')

    print("Takip turu bitti.")
