"use client";
// Adet sorusu boş bırakılırsa (ya da elindeki adetten büyükse) TAMAMI satılır;
// sayı girilirse kısmi kapama yapılır, pozisyon açık kalır (kurtarma planının
// "kısmi çıkış öner" önerisini artık sitede uygulayabilirsin — plan bölüm 8).

export default function KapatButton({ id, symbol, adet }: { id: string; symbol: string; adet: number }) {
  return (
    <form
      method="post"
      action="/api/pozisyon/kapat"
      onSubmit={(e) => {
        const adetGiris = window.prompt(
          `${symbol}: kaç adet satıldı? (elinde ${adet} adet var — boş bırakırsan TAMAMI satılır)`,
        );
        if (adetGiris === null) {
          e.preventDefault();
          return;
        }
        const onayMetin = adetGiris.trim()
          ? `${symbol}: ${adetGiris} adet satılacak. Emin misin?`
          : `${symbol} pozisyonunun TAMAMI kapatılacak. Emin misin?`;
        if (!window.confirm(onayMetin)) {
          e.preventDefault();
          return;
        }
        const fiyat = window.prompt(
          "Satış fiyatın ne? (getiri hesabı için — boş bırakılırsa %0 sayılır)",
        ) ?? "";
        const neden = window.prompt("Neden sattın? (boş bırakılabilir)") ?? "";
        const el = e.currentTarget.elements;
        (el.namedItem("adet") as HTMLInputElement).value = adetGiris.trim();
        (el.namedItem("fiyat") as HTMLInputElement).value = fiyat;
        (el.namedItem("neden") as HTMLInputElement).value = neden;
      }}
    >
      <input type="hidden" name="id" value={id} />
      <input type="hidden" name="adet" value="" />
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
