"""Günlük rapor girişi.

Kullanım: python report.py BIST | US | auto
'auto': UTC saatine göre karar verir (öğleden önce=BIST sabah raporu,
akşam=ABD kapanış raporu) — tek workflow iki cron'la çalışabilsin diye.
"""
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from src import report

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "auto"
    if arg == "auto":
        market = "BIST" if datetime.now(timezone.utc).hour < 12 else "US"
    else:
        market = arg.upper()
    print(f"{market} raporu hazırlanıyor...")
    sections = report.build_and_send(market)
    print(f"Gönderilen bölümler: {', '.join(sections)}")
