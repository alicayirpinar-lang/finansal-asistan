import Link from "next/link";
import { db } from "@/lib/supabase";
import { DURUM, GUVEN, YON, tarih } from "@/lib/labels";

export const dynamic = "force-dynamic";

const FILTRELER = [
  { key: "", label: "Hepsi" },
  { key: "acik", label: "Açık" },
  { key: "hedefe_ulasti", label: "Hedefe ulaştı" },
  { key: "tez_bozuldu", label: "Bozuldu" },
  { key: "suresi_doldu", label: "Süresi doldu" },
];

export default async function TezlerPage({
  searchParams,
}: {
  searchParams: Promise<{ durum?: string }>;
}) {
  const { durum } = await searchParams;
  let query = db().from("theses")
    .select("id,symbol,market,category,direction,final_confidence,notification_tier,status,horizon,target_range_pct,created_at")
    .neq("status", "iptal_edildi")
    .order("created_at", { ascending: false }).limit(100);
  if (durum) query = query.eq("status", durum);
  const { data: tezler } = await query;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        {FILTRELER.map((f) => (
          <Link key={f.key} href={f.key ? `/tezler?durum=${f.key}` : "/tezler"}
            className={`text-xs rounded-full px-3 py-1 border ${
              (durum ?? "") === f.key
                ? "border-emerald-500 text-emerald-300"
                : "border-zinc-700 text-zinc-400 hover:border-zinc-500"
            }`}>
            {f.label}
          </Link>
        ))}
      </div>

      {tezler?.length ? (
        <ul className="space-y-2">
          {tezler.map((t) => (
            <li key={t.id}>
              <Link href={`/tez/${t.id}`}
                className="block rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-3 hover:border-zinc-600">
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="font-medium">{t.symbol}</span>
                  <span className="text-xs text-zinc-500">{t.market}</span>
                  <span className="text-xs text-zinc-400">{YON[t.direction] ?? t.direction}</span>
                  <span className={`text-xs rounded px-2 py-0.5 ${DURUM[t.status]?.cls ?? ""}`}>
                    {DURUM[t.status]?.label ?? t.status}
                  </span>
                  <span className="ml-auto text-xs text-zinc-500">{tarih(t.created_at)}</span>
                </div>
                <div className="mt-1 text-xs text-zinc-400">
                  güven: {GUVEN[t.final_confidence] ?? "-"} · hedef {t.target_range_pct} ·
                  ufuk {t.horizon} · kategori {t.category}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-zinc-500">Bu filtrede tez yok.</p>
      )}
    </div>
  );
}
