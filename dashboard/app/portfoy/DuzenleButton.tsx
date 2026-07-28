"use client";
// Yanlış girilen adet/fiyat/tarihi düzeltmek için — Kapat/Sil'e gerek kalmadan
// pozisyon yerinde güncellenir, tez/durum hiç etkilenmez (28 Temmuz 2026).

export default function DuzenleButton({
  id, symbol, adet, fiyat, tarih,
}: { id: string; symbol: string; adet: number; fiyat: number; tarih: string }) {
  return (
    <form
      method="post"
      action="/api/pozisyon/duzenle"
      onSubmit={(e) => {
        const yeniAdet = window.prompt(`${symbol}: adet`, String(adet));
        if (yeniAdet === null) { e.preventDefault(); return; }
        const yeniFiyat = window.prompt(`${symbol}: alış fiyatı`, String(fiyat));
        if (yeniFiyat === null) { e.preventDefault(); return; }
        const yeniTarih = window.prompt(`${symbol}: alış tarihi (YYYY-AA-GG)`, tarih);
        if (yeniTarih === null) { e.preventDefault(); return; }
        const el = e.currentTarget.elements;
        (el.namedItem("adet") as HTMLInputElement).value = yeniAdet.trim();
        (el.namedItem("fiyat") as HTMLInputElement).value = yeniFiyat.trim();
        (el.namedItem("tarih") as HTMLInputElement).value = yeniTarih.trim();
      }}
    >
      <input type="hidden" name="id" value={id} />
      <input type="hidden" name="adet" value="" />
      <input type="hidden" name="fiyat" value="" />
      <input type="hidden" name="tarih" value="" />
      <button
        type="submit"
        className="text-xs rounded border border-zinc-700 text-zinc-300 px-2 py-0.5 hover:bg-zinc-800"
      >
        Düzenle
      </button>
    </form>
  );
}
