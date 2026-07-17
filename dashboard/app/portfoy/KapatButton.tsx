"use client";
// Yanlışlıkla tek tıkla kapamayı önlemek için tarayıcı onayı ister;
// satış fiyatı (getiri hesabı için) ve opsiyonel "neden" notu da burada alınır.

export default function KapatButton({ id, symbol }: { id: string; symbol: string }) {
  return (
    <form
      method="post"
      action="/api/pozisyon/kapat"
      onSubmit={(e) => {
        if (!window.confirm(`${symbol} pozisyonunun TAMAMI kapatılacak. Emin misin?`)) {
          e.preventDefault();
          return;
        }
        const fiyat = window.prompt(
          "Satış fiyatın ne? (getiri hesabı için — boş bırakılırsa %0 sayılır)",
        ) ?? "";
        const neden = window.prompt("Neden sattın? (boş bırakılabilir)") ?? "";
        const el = e.currentTarget.elements;
        (el.namedItem("fiyat") as HTMLInputElement).value = fiyat;
        (el.namedItem("neden") as HTMLInputElement).value = neden;
      }}
    >
      <input type="hidden" name="id" value={id} />
      <input type="hidden" name="fiyat" value="" />
      <input type="hidden" name="neden" value="" />
      <button
        type="submit"
        className="text-xs rounded border border-red-900 text-red-400 px-2 py-0.5 hover:bg-red-950"
      >
        Kapat
      </button>
    </form>
  );
}
