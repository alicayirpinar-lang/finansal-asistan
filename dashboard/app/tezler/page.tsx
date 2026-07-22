import Link from "next/link";
import { db } from "@/lib/supabase";
import { DURUM, GUVEN, KAYNAK, YON, tarih } from "@/lib/labels";

export const dynamic = "force-dynamic";

const FILTRELER = [
  { key: "", label: "Hepsi" },
  { key: "acik", label: "Açık" },
  { key: "hedefe_ulasti", label: "Hedefe ulaştı" },
  { key: "tez_bozuldu", label: "Bozuldu" },
  { key: "suresi_doldu", label: "Süresi doldu" },
];

const KAYNAKLAR = [
  { key: "", label: "Kaynak: hepsi" },
  { key: "haber", label: "Haber" },
  { key: "teknik", label: "Teknik radar" },
  { key: "ikinci_derece", label: "İkinci derece" },
  { key: "geriye_donuk", label: "Geriye dönük" },
];

function chipHref(durum: string, sembol: string, kaynak: string, yeniDurum: string) {
  const p = new URLSearchParams();
  if (yeniDurum) p.set("durum", yeniDurum);
  if (sembol) p.set("sembol", sembol);
  if (kaynak) p.set("kaynak", kaynak);
  const q = p.toString();
  return q ? `/tezler?${q}` : "/tezler";
}

export default async function TezlerPage({
  searchParams,
}: {
  searchParams: Promise<{ durum?: string; sembol?: string; kaynak?: string }>;
}) {
  const { durum, sembol, kaynak } = await searchParams;
  let query = db().from("theses")
    .select("id,symbol,market,category,direction,final_confidence,notification_tier,status,kaynak,horizon,target_range_pct,created_at,resolved_at")
    .neq("status", "iptal_edildi")
    .order("created_at", { ascending: false }).limit(100);
  if (durum) query = query.eq("status", durum);
  if (kaynak) query = query.eq("kaynak", kaynak);
  if (sembol) query = query.ilike("symbol", `%${sembol.trim().toUpperCase()}%`);
  const { data: tezler } = await query;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        {FILTRELER.map((f) => (
          <Link key={f.key} href={chipHref(durum ?? "", sembol ?? "", kaynak ?? "", f.key)}
            className={`text-xs rounded-full px-3 py-1 border ${
              (durum ?? "") === f.key
                ? "border-emerald-500 text-emerald-300"
                : "border-zinc-700 text-zinc-400 hover:border-zinc-500"
            }`}>
            {f.label}
          </Link>
        ))}
      </div>

      <form method="get" className="flex flex-wrap items-end gap-3">
        {durum && <input type="hidden" name="durum" value={durum} />}
        <label className="text-xs text-zinc-400 space-y-1">
          <span>Sembol ara</span>
          <input name="sembol" defaultValue={sembol ?? ""} placeholder="THYAO"
            className="block rounded border border-zinc-700 bg-zinc-800 px-2 py-1.5 text-sm w-32 uppercase" />
        </label>
        <label className="text-xs text-zinc-400 space-y-1">
          <span>Kaynak</span>
          <select name="kaynak" defaultValue={kaynak ?? ""}
            className="block rounded border border-zinc-700 bg-zinc-800 px-2 py-1.5 text-sm">
            {KAYNAKLAR.map((k) => (
              <option key={k.key} value={k.key}>{k.label}</option>
            ))}
          </select>
        </label>
        <button type="submit"
          className="rounded bg-emerald-700 hover:bg-emerald-600 px-3 py-1.5 text-sm font-medium">
          Filtrele
        </button>
        {(sembol || kaynak) && (
          <Link href={chipHref(durum ?? "", "", "", durum ?? "")}
            className="text-xs text-zinc-500 hover:text-zinc-300 underline">
            filtreleri temizle
          </Link>
        )}
      </form>

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
                  <span className={`text-xs rounded px-2 py-0.5 ${KAYNAK[t.kaynak]?.cls ?? "bg-zinc-700 text-zinc-200"}`}>
                    {KAYNAK[t.kaynak]?.label ?? t.kaynak ?? "haber"}
                  </span>
                  <span className="ml-auto text-xs text-zinc-500">
                    {t.resolved_at ? `sonuçlandı: ${tarih(t.resolved_at)}` : tarih(t.created_at)}
                  </span>
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
