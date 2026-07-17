"""Aşama 1 duman testi: kimlik bilgisi gerektirmez (RSS + filtre)."""
from src import collector, filter as f1

items, errors = collector.collect_news()
print(f"Toplam haber: {len(items)}")
print(f"Kaynak hatalari: {len(errors)}")
for name, err in errors:
    print(f"  ! {name}: {err[:90]}")

clusters = f1.dedup(items)
print(f"Dedup: {len(items)} haber -> {len(clusters)} kume")

events = f1.build_events(clusters)
print(f"Skorlu olay: {len(events)}\n")
print("Ilk 10 olay:")
for e in events[:10]:
    print(f'  [{e["priority_lane"]:13}] {e["symbol"]:6} skor={e["relevance_score"]:.2f} '
          f'{e["category"]:10} | {e["title"][:65]}')
