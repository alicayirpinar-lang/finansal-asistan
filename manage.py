"""Portföy CLI (v1). Telegram bot komutları buluta taşıma aşamasında gelecek;
o zamana kadar pozisyonlar buradan girilir.

Örnekler:
  python manage.py ekle --tur deneme --sembol USO --adet 10 --fiyat 78.5 --tarih 2026-07-17
  python manage.py ekle --tur deneme --sembol THYAO --adet 100 --fiyat 285 --tarih 2026-07-17 --tez <TEZ_ID>
  python manage.py kapat --sembol USO
  python manage.py durum --tur deneme
  python manage.py tezler
"""
import argparse

from dotenv import load_dotenv

load_dotenv()

from config import SYMBOLS
from src import metrics, storage


def cmd_ekle(args):
    if args.sembol not in SYMBOLS:
        print(f"Bilinmeyen sembol: {args.sembol}. config.py'deki listeye bak.")
        return
    pos = storage.add_position(
        symbol=args.sembol, market=SYMBOLS[args.sembol]["market"],
        quantity=args.adet, entry_price=args.fiyat, entry_date=args.tarih,
        portfolio_type=args.tur, thesis_id=args.tez,
    )
    print(f'Eklendi [{args.tur}]: {args.adet} x {args.sembol} @ {args.fiyat} (id={pos["id"][:8]})')
    if not args.tez:
        print("Not: Bu dışarıdan bir pozisyon. Geriye dönük tez istersen dashboard'daki "
              "formdan (kutucuğu işaretleyerek) girmen gerekir.")


def cmd_kapat(args):
    if args.fiyat is None:
        print("Uyarı: --fiyat verilmedi; gerçekleşen K/Z hesabında %0 varsayılacak.")
    pos = storage.close_position(args.sembol, args.adet, args.neden, args.fiyat)
    if pos is None:
        print(f"{args.sembol} için açık pozisyon bulunamadı.")
    else:
        print(f'{args.sembol} kapatıldı' + (f' (kısmi: {args.adet})' if args.adet else ' (tamamı)'))
        try:
            metrics.compute_and_store()
        except Exception as e:
            print(f"Getiri metrikleri hesaplanamadı: {str(e)[:120]}")


def cmd_durum(args):
    rows = storage.list_positions(args.tur)
    if not rows:
        print("Açık pozisyon yok.")
        return
    for p in rows:
        print(f'[{p["portfolio_type"]:6}] {p["symbol"]:6} {p["quantity"]} adet @ {p["entry_price"]} '
              f'({p["entry_date"]})' + ('  [teze bağlı]' if p.get("thesis_id") else '  [dışarıdan]'))


def cmd_tezler(args):
    rows = (storage.get_client().table("theses")
            .select("id,symbol,market,direction,final_confidence,notification_tier,status,created_at")
            .eq("status", "acik").order("created_at", desc=True).execute().data)
    if not rows:
        print("Açık tez yok.")
        return
    for t in rows:
        print(f'{t["id"][:8]}  {t["symbol"]:6} {t["market"]:4} {t["direction"]:8} '
              f'güven={t["final_confidence"]:6} katman={t["notification_tier"]:6} {t["created_at"][:10]}')


def build_parser():
    p = argparse.ArgumentParser(description="Finansal asistan portföy yönetimi (v1)")
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("ekle", help="pozisyon ekle")
    e.add_argument("--tur", required=True, choices=["gercek", "deneme"],
                   help="bilinçli seçim zorunlu — varsayılan yok")
    e.add_argument("--sembol", required=True)
    e.add_argument("--adet", required=True, type=float)
    e.add_argument("--fiyat", required=True, type=float)
    e.add_argument("--tarih", required=True, help="YYYY-AA-GG")
    e.add_argument("--tez", default=None, help="bağlı tez id (opsiyonel)")
    e.set_defaults(func=cmd_ekle)

    k = sub.add_parser("kapat", help="pozisyon kapat")
    k.add_argument("--sembol", required=True)
    k.add_argument("--adet", type=float, default=None, help="kısmi kapama adedi")
    k.add_argument("--fiyat", type=float, default=None, help="satış fiyatı (getiri hesabı için)")
    k.add_argument("--neden", default=None)
    k.set_defaults(func=cmd_kapat)

    d = sub.add_parser("durum", help="açık pozisyonları listele")
    d.add_argument("--tur", choices=["gercek", "deneme"], default=None)
    d.set_defaults(func=cmd_durum)

    t = sub.add_parser("tezler", help="açık tezleri listele")
    t.set_defaults(func=cmd_tezler)
    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)
