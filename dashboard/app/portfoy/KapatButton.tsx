"use client";
// Yanlışlıkla tek tıkla kapamayı önlemek için tarayıcı onayı ister;
// opsiyonel "neden sattın" notu da burada alınır (plan bölüm 8).

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
        const neden = window.prompt("Neden sattın? (boş bırakılabilir)") ?? "";
        (e.currentTarget.elements.namedItem("neden") as HTMLInputElement).value = neden;
      }}
    >
      <input type="hidden" name="id" value={id} />
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
