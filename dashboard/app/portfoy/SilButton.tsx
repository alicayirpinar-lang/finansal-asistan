"use client";
// Kapat'tan bilinçli olarak ayrı: bu GERÇEK bir satış değil, yanlış giriş
// düzeltmesi içindir — bağlı tez varsa etkilenmez (28 Temmuz 2026, RCL vakası).

export default function SilButton({ id, symbol }: { id: string; symbol: string }) {
  return (
    <form
      method="post"
      action="/api/pozisyon/sil"
      onSubmit={(e) => {
        const onay = window.confirm(
          `${symbol} pozisyonu TAMAMEN silinecek.\n\n` +
          "Bunu SADECE yanlış giriş (yanlış sembol/adet/fiyat) düzeltmesi için kullan — " +
          "gerçekten sattıysan bunun yerine 'Kapat'ı kullan.\n\n" +
          "Bağlı bir tez varsa ETKİLENMEZ, kendi haline (açık) devam eder. Emin misin?",
        );
        if (!onay) e.preventDefault();
      }}
    >
      <input type="hidden" name="id" value={id} />
      <button
        type="submit"
        className="text-xs rounded border border-zinc-700 text-zinc-500 px-2 py-0.5 hover:bg-zinc-800"
      >
        Sil (yanlış giriş)
      </button>
    </form>
  );
}
