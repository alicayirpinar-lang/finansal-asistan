"""Telegram bildirimleri. v1: kritik ve orta tezler mesaj olarak gider,
gözlem sadece veritabanına yazılır (günlük rapor buluta taşınınca gelecek).
"""
import os

import requests

from src import storage

TIMEOUT = 30
_EMOJI = {"kritik": "🚨", "orta": "ℹ️"}
_GUVEN = {"dusuk": "düşük", "orta": "orta", "yuksek": "yüksek"}
_KURULUM_ADI = {"taban_kirilimi": "taban kırılımı", "sikisma_kirilim_adayi": "sıkışma kırılım adayı"}


def send(text, tur="diger"):
    """Giden HER mesaj (başarılı/başarısız) mesaj_log'a yazılır — dashboard
    mesajlaşma merkezinin (/bildirimler) veri kaynağı, faz 12 sonrası eklendi
    (önceden sadece tez bildirimleri alerts'e loglanıyordu, rapor/teknik
    fırsat mesajları hiçbir yerde görünmüyordu)."""
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        msg_id = resp.json()["result"]["message_id"]
    except Exception as e:
        _log_mesaj(tur, text, False, None, str(e)[:300])
        raise
    _log_mesaj(tur, text, True, msg_id, None)
    return msg_id


def _log_mesaj(tur, text, basarili, telegram_message_id, hata_metni):
    try:
        storage.log_mesaj(tur, text[:500], basarili, telegram_message_id, hata_metni)
    except Exception:
        pass  # mesaj loglama başarısız oldu diye gönderim akışı bozulmasın


def format_thesis(event, draft, redteam, final_confidence, tier):
    low, high = draft["buyukluk_araligi_pct"]
    inv = redteam.get("gecersiz_kilma_kosulu") or {}
    chain_txt = "\n".join(
        f'  {a["adim_no"]}. {a["mekanizma"]} [{_GUVEN.get(a["guven"], a["guven"])}]'
        for a in draft["zincir"]
    )
    weak = redteam.get("en_zayif_halka") or {}
    return (
        f'{_EMOJI.get(tier, "")} {"KRİTİK TEZ" if tier == "kritik" else "Yeni tez"}\n'
        f'{event["symbol"]} ({event["market"]}) — {"yükseliş" if draft["yon"] == "yukselis" else "düşüş"} beklentisi\n\n'
        f'Olay: {event["title"]}\n\n'
        f'Zincir:\n{chain_txt}\n\n'
        f'Güven: {_GUVEN[final_confidence]}\n'
        f'Hedef: %{low}-{high} · Ufuk: {draft.get("ufuk_deger", "?")} {draft["ufuk"]}\n'
        f'Tezi bozan koşul: {inv.get("kosul", "-")}\n'
        f'En zayıf halka: {weak.get("aciklama", "-")}\n\n'
        f'⚠️ Bu bir analiz, yatırım tavsiyesi değil. Karar senin.'
    )


def format_teknik_firsat(aday, market, rejim_bilgi):
    """Faz 12 A — teknik radar bildirimi. AI hikayesi YOK, kasıtlı olarak
    format_thesis'ten farklı: istatistiksel kurulum, yatırım hikayesi değil."""
    s = aday["kurulum"]
    return (
        f'📈 TEKNİK FIRSAT\n'
        f'{aday["symbol"]} ({market}) — {_KURULUM_ADI.get(s["ad"], s["ad"])} (skor {s["skor"]})\n\n'
        f'Koşullar: {"; ".join(s["kosullar"])}\n'
        f'Backtest kanıtı: örneklem-dışı medyan getiri taban çizgisini geçiyor '
        f'(bkz. tools/backtest_kurulum.py)\n\n'
        f'Giriş: {aday["entry"]} · Stop: {aday["stop"]} (2×ATR) · '
        f'Hedef: %{aday["hedef_dusuk"]}-{aday["hedef_yuksek"]} (~1 ay ufuk) · R/Ö ~{aday["rr"]}x\n'
        f'Piyasa rejimi: {rejim_bilgi.get("rejim")}\n\n'
        f'⚠️ Bu bir AI hikayesi değil, istatistiksel bir kurulumdur — geçmişte '
        f'~%55-60 kazanma oranı, her sinyal kazanmaz. Yatırım tavsiyesi değildir.'
    )
