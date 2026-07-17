"""Geriye dönük tez kuyruğu uçtan uca testi (bkz. src/retro.py).

Deneme portföyüne test pozisyonu + kuyruk kaydı ekler, haberleri toplayıp
kuyruğu işler, sonucu yazdırır. Test verisini silmez — temizlik ayrı yapılır.
"""
import os
from dotenv import load_dotenv

load_dotenv()

from src import collector, filter as f1, retro, storage

SYMBOL = "NVDA"

pos = storage.add_position(SYMBOL, "US", 1, 170.0, "2026-07-17", "deneme")
print(f"Test pozisyonu: {pos['id']}")

req = (storage.get_client().table("retro_thesis_queue")
       .insert({"position_id": pos["id"], "symbol": SYMBOL}).execute().data[0])
print(f"Kuyruk kaydı: {req['id']}")

items, errors = collector.collect_news()
print(f"{len(items)} haber toplandı ({len(errors)} kaynak hatası)")
clusters = f1.dedup(items)

cap = int(os.environ.get("DAILY_GEMINI_CAP", "40"))
retro.process_queue(clusters, cap)

son = (storage.get_client().table("retro_thesis_queue").select("*")
       .eq("id", req["id"]).execute().data[0])
pos_son = storage.get_position(pos["id"])
print(f"\nKuyruk durumu: {son['status']} — {son['note']}")
print(f"Pozisyon thesis_id: {pos_son['thesis_id']}")
print(f"\nTemizlik için: pozisyon={pos['id']} kuyruk={req['id']}")
