import Link from "next/link";
import { db } from "@/lib/supabase";
import { DURUM, tarih } from "@/lib/labels";

export const dynamic = "force-dynamic";

/* eslint-disable @typescript-eslint/no-explicit-any */

async function sonFiyatlar(symbols: string[]): Promise<Record<string, number>> {
  // Panelde canlı fiyat çekmiyoruz; takip turlarının kaydettiği son fiyatı kullanıyoruz.
  if (!symbols.length) return {};
  const { data } = await db().from("thesis_checks")
    .select("price_at_check,checked_at,theses!inner(symbol)")
    .in("theses.symbol", symbols)
    .order("checked_at", { ascending: false }).limit(200);
  const out: Record<string, number> = {};
  for (const row of (data ?? []) as any[]) {
    const sym = row.theses?.symbol;
    if (sym && row.price_at_check && !(sym in out)) out[sym] = Number(row.price_at_check);
  }
  return out;
}

function Grup({ baslik, rows, fiyatlar, uyari }: {
  baslik: string; rows: any[]; fiyatlar: Record<string, number>; uyari?: string;
}) {
  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
      <h2 className="text-sm font-semibold text-zinc-400 uppercase mb-1">{baslik}</h2>
      {uyari && <p className="text-xs text-zinc-500 mb-3">{uyari}</p>}
      {rows.length ? (
        <ul className="space-y-2">
          {rows.map((p) => {
            const guncel = fiyatlar[p.symbol];
            const pnl = guncel
              ? ((guncel - Number(p.entry_price)) / Number(p.entry_price)) * 100
              : null;
            return (
              <li key={p.id} className="flex items-center gap-3 text-sm flex-wrap">
                <span className="font-medium w-16">{p.symbol}</span>
                <span className="text-zinc-400">{Number(p.quantity)} adet @ {p.entry_price}</span>
                {pnl !== null ? (
                  <span className={pnl >= 0 ? "text-emerald-400" : "text-red-400"}>
                    %{pnl >= 0 ? "+" : ""}{pnl.toFixed(1)}
                  </span>
                ) : (
                  <span className="text-zinc-600 text-xs">son fiyat yok</span>
                )}
                <span className="text-xs text-zinc-500">{p.entry_date}</span>
                {p.thesis_id ? (
                  <Link href={`/tez/${p.thesis_id}`} className="text-xs text-blue-400 hover:underline">
                    tez →
                  </Link>
                ) : (
                  <span className="text-xs text-zinc-600">tez yok</span>
                )}
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="text-sm text-zinc-500">Pozisyon yok.</p>
      )}
    </section>
  );
}

export default async function PortfoyPage() {
  const { data: rows } = await db().from("portfolio").select("*")
    .eq("status", "acik").order("entry_date", { ascending: false });
  const positions = rows ?? [];
  const fiyatlar = await sonFiyatlar([...new Set(positions.map((p) => p.symbol))]);

  return (
    <div className="space-y-5">
      <Grup baslik="Gerçek portföy" fiyatlar={fiyatlar}
        rows={positions.filter((p) => p.portfolio_type === "gercek")} />
      <Grup baslik="Deneme portföyü" fiyatlar={fiyatlar}
        rows={positions.filter((p) => p.portfolio_type === "deneme")}
        uyari="Sanal — gerçek para değildir, gerçek toplamlara asla dahil edilmez." />
      <p className="text-xs text-zinc-500">
        Fiyatlar son takip turundan alınır (canlı değildir). Pozisyon ekleme/kapama şimdilik
        bilgisayardaki manage.py üzerinden yapılır.
      </p>
    </div>
  );
}
