"""Telegram bildirimleri. v1: kritik ve orta tezler mesaj olarak gider,
gözlem sadece veritabanına yazılır (günlük rapor buluta taşınınca gelecek).
"""
import os

import requests

TIMEOUT = 30
_EMOJI = {"kritik": "🚨", "orta": "ℹ️"}
_GUVEN = {"dusuk": "düşük", "orta": "orta", "yuksek": "yüksek"}


def send(text):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["result"]["message_id"]


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
