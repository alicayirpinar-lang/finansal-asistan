// Mesajlaşma merkezi — sisteme giden HER Telegram mesajının (başarılı/
// başarısız) kaydı. Önceden sadece tez yaşam-döngüsü bildirimleri (alerts)
// loglanıyordu; rapor/teknik fırsat/geriye dönük mesajlar hiç görünmüyordu.
import Link from "next/link";
import { db } from "@/lib/supabase";
import { MESAJ_TUR, tarih } from "@/lib/labels";

export const dynamic = "force-dynamic";

const TURLER = ["", ...Object.keys(MESAJ_TUR)];

export default async function BildirimlerPage({
  searchParams,
}: {
  searchParams: Promise<{ tur?: string }>;
}) {
  const { tur } = await searchParams;
  let query = db().from("mesaj_log").select("*")
    .order("created_at", { ascending: false }).limit(100);
  if (tur) query = query.eq("tur", tur);
  const { data: mesajlar } = await query;

  return (
    <div className="space-y-4">
      <p className="text-xs text-zinc-500">
        Sisteme giden her Telegram mesajının kaydı — ne geldi, ne başarısız oldu.
        Son 100 mesaj.
      </p>

      <form method="get" className="flex items-end gap-3">
        <label className="text-xs text-zinc-400 space-y-1">
          <span>Tür</span>
          <select name="tur" defaultValue={tur ?? ""}
            className="block rounded border border-zinc-700 bg-zinc-800 px-2 py-1.5 text-sm min-w-[220px]">
            {TURLER.map((t) => (
              <option key={t} value={t}>{t ? (MESAJ_TUR[t] ?? t) : "Hepsi"}</option>
            ))}
          </select>
        </label>
        <button type="submit"
          className="rounded bg-emerald-700 hover:bg-emerald-600 px-3 py-1.5 text-sm font-medium">
          Filtrele
        </button>
        {tur && (
          <Link href="/bildirimler" className="text-xs text-zinc-500 hover:text-zinc-300 underline">
            filtreyi temizle
          </Link>
        )}
      </form>

      {mesajlar?.length ? (
        <ul className="space-y-2">
          {mesajlar.map((m) => (
            <li key={m.id} className={`rounded-lg border px-4 py-3 ${
              m.basarili ? "border-zinc-800 bg-zinc-900" : "border-red-900 bg-red-950/30"
            }`}>
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-xs rounded px-2 py-0.5 bg-zinc-800 text-zinc-300">
                  {MESAJ_TUR[m.tur] ?? m.tur}
                </span>
                {!m.basarili && (
                  <span className="text-xs rounded px-2 py-0.5 bg-red-900 text-red-200">
                    gönderilemedi
                  </span>
                )}
                <span className="ml-auto text-xs text-zinc-500">{tarih(m.created_at)}</span>
              </div>
              <p className="mt-1.5 text-sm text-zinc-300 whitespace-pre-line line-clamp-4">
                {m.icerik}
              </p>
              {m.hata_metni && (
                <p className="mt-1 text-xs text-red-400">Hata: {m.hata_metni}</p>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-zinc-500">Bu filtrede mesaj yok.</p>
      )}
    </div>
  );
}
