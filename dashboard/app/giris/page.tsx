export default async function GirisPage({
  searchParams,
}: {
  searchParams: Promise<{ hata?: string }>;
}) {
  const { hata } = await searchParams;
  return (
    <div className="max-w-sm mx-auto mt-24">
      <h1 className="text-xl font-semibold mb-4">Giriş</h1>
      <form method="POST" action="/api/giris" className="space-y-3">
        <input
          type="password" name="sifre" placeholder="Panel şifresi" autoFocus
          className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-emerald-500"
        />
        <button
          type="submit"
          className="w-full rounded-md bg-emerald-600 py-2 text-sm font-medium hover:bg-emerald-500">
          Gir
        </button>
        {hata && <p className="text-sm text-red-400">Şifre yanlış.</p>}
      </form>
    </div>
  );
}
