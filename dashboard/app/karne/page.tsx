import Link from "next/link";
import { db } from "@/lib/supabase";
import { DURUM, GUVEN, KAYNAK, gunSayisi, tarih } from "@/lib/labels";

export const dynamic = "force-dynamic";

/* eslint-disable @typescript-eslint/no-explicit-any */

function Sapma({ gun, beklenen }: { gun: number | null; beklenen: number | null }) {
  if (gun === null || beklenen === null) return <span className="text-zinc-600">-</span>;
  const fark = gun - beklenen;
  if (fark === 0) return <span className="text-zinc-400">tam zamanında</span>;
  const erken = fark < 0;
  return (
    <span className={erken ? "text-emerald-400" : "text-amber-400"}>
      {Math.abs(fark)} gün {erken ? "erken" : "geç"}
    </span>
  );
}

async function sonuclananTezler() {
  const { data } = await db().from("theses")
    .select("id,symbol,market,status,kaynak,category,final_confidence,created_at,resolved_at,expected_horizon_days")
    .in("status", ["hedefe_ulasti", "tez_bozuldu", "suresi_doldu"])
    .order("resolved_at", { ascending: false }).limit(50);
  return data ?? [];
}

export default async function KarnePage() {
  const [{ data: rows }, sonuclananlar] = await Promise.all([
    db().from("isabet_karnesi").select("*"),
    sonuclananTezler(),
  ]);

  return (
    <div className="space-y-8">
      <section className="space-y-4">
        <h2 className="text-sm font-semibold text-zinc-400 uppercase">Sonuçlanan tezler</h2>
        <p className="text-xs text-zinc-500">
          Beklenen gün, tez açılırken sistemin kendi ufuk tahminidir (AI). Sapma büyükse
          (özellikle sistematik olarak hep erken/geç), ufuk tahmini örneklem birikince
          kalibre edilecek.
        </p>
        {sonuclananlar.length ? (
          <div className="overflow-x-auto rounded-lg border border-zinc-800">
            <table className="w-full text-sm">
              <thead className="bg-zinc-900 text-zinc-400 text-xs uppercase">
                <tr>
                  {["Sembol", "Durum", "Kaynak", "Beklenen gün", "Gerçekleşen gün", "Sapma", "Sonuç tarihi"].map((h) => (
                    <th key={h} className="px-3 py-2 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sonuclananlar.map((t: any) => {
                  const gercek = gunSayisi(t.created_at, t.resolved_at);
                  return (
                    <tr key={t.id} className="border-t border-zinc-800">
                      <td className="px-3 py-2">
                        <Link href={`/tez/${t.id}`} className="font-medium hover:underline">
                          {t.symbol}
                        </Link>
                        <span className="text-zinc-500 text-xs ml-1">{t.market}</span>
                      </td>
                      <td className="px-3 py-2">
                        <span className={`text-xs rounded px-2 py-0.5 ${DURUM[t.status]?.cls ?? ""}`}>
                          {DURUM[t.status]?.label ?? t.status}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-zinc-400">{KAYNAK[t.kaynak]?.label ?? t.kaynak ?? "-"}</td>
                      <td className="px-3 py-2 text-zinc-400">
                        {t.expected_horizon_days ?? "-"}{t.expected_horizon_days ? " gün" : ""}
                      </td>
                      <td className="px-3 py-2 text-zinc-400">{gercek !== null ? `${gercek} gün` : "-"}</td>
                      <td className="px-3 py-2"><Sapma gun={gercek} beklenen={t.expected_horizon_days} /></td>
                      <td className="px-3 py-2 text-xs text-zinc-500">{tarih(t.resolved_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-zinc-500">Henüz sonuçlanmış tez yok.</p>
        )}
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold text-zinc-400 uppercase">İsabet oranı özeti</h2>
        <p className="text-xs text-zinc-500">
          İsabet karnesi sonuçlanmış tezlerden hesaplanır (süresi dolanlar orana girmez).
          İlk aylarda örneklem küçüktür — oranlara ihtiyatla yaklaş (soğuk başlangıç dönemi).
        </p>
        {rows?.length ? (
        <div className="overflow-x-auto rounded-lg border border-zinc-800">
          <table className="w-full text-sm">
            <thead className="bg-zinc-900 text-zinc-400 text-xs uppercase">
              <tr>
                {["Kaynak", "Kategori", "Pazar", "Güven", "Başarılı", "Başarısız", "Sonuçsuz", "İsabet"].map((h) => (
                  <th key={h} className="px-3 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} className="border-t border-zinc-800">
                  <td className="px-3 py-2 text-zinc-400">{r.kaynak ?? "-"}</td>
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
      </section>
    </div>
  );
}
