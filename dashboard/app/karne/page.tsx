import { db } from "@/lib/supabase";
import { GUVEN } from "@/lib/labels";

export const dynamic = "force-dynamic";

export default async function KarnePage() {
  const { data: rows } = await db().from("isabet_karnesi").select("*");

  return (
    <div className="space-y-4">
      <p className="text-xs text-zinc-500">
        İsabet karnesi sonuçlanmış tezlerden hesaplanır (süresi dolanlar orana girmez).
        İlk aylarda örneklem küçüktür — oranlara ihtiyatla yaklaş (soğuk başlangıç dönemi).
      </p>
      {rows?.length ? (
        <div className="overflow-x-auto rounded-lg border border-zinc-800">
          <table className="w-full text-sm">
            <thead className="bg-zinc-900 text-zinc-400 text-xs uppercase">
              <tr>
                {["Kategori", "Pazar", "Güven", "Başarılı", "Başarısız", "Sonuçsuz", "İsabet"].map((h) => (
                  <th key={h} className="px-3 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} className="border-t border-zinc-800">
                  <td className="px-3 py-2">{r.category}</td>
                  <td className="px-3 py-2 text-zinc-400">{r.market}</td>
                  <td className="px-3 py-2">{GUVEN[r.final_confidence] ?? r.final_confidence}</td>
                  <td className="px-3 py-2 text-emerald-400">{r.basarili}</td>
                  <td className="px-3 py-2 text-red-400">{r.basarisiz}</td>
                  <td className="px-3 py-2 text-zinc-400">{r.sonucsuz}</td>
                  <td className="px-3 py-2 font-medium">
                    {r.isabet_orani !== null ? `%${Math.round(Number(r.isabet_orani) * 100)}` : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-zinc-500">
          Henüz sonuçlanmış tez yok — ilk tezler hedefe ulaştığında ya da bozulduğunda
          karne burada oluşmaya başlayacak.
        </p>
      )}
    </div>
  );
}
