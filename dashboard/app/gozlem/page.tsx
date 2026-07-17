import { db } from "@/lib/supabase";
import { tarih } from "@/lib/labels";

export const dynamic = "force-dynamic";

export default async function GozlemPage() {
  const { data: rows } = await db().from("technical_signals")
    .select("symbol,market,computed_at,volume_z,rsi,ma20_cross,pct_from_52w,signal_count,gozlem_skoru")
    .gt("gozlem_skoru", 0)
    .order("computed_at", { ascending: false }).limit(50);

  return (
    <div className="space-y-4">
      <p className="text-xs text-zinc-500">
        Gözlemlenen istatistiksel anormallikler — sebep içermez, tez değildir.
        Bir sembol ancak en az 2 gösterge aynı yönde tetiklenirse burada görünür.
      </p>
      {rows?.length ? (
        <div className="overflow-x-auto rounded-lg border border-zinc-800">
          <table className="w-full text-sm">
            <thead className="bg-zinc-900 text-zinc-400 text-xs uppercase">
              <tr>
                {["Sembol", "Pazar", "Skor", "Hacim z", "RSI", "MA20 kesişim", "52h uzaklık %", "Tarih"].map((h) => (
                  <th key={h} className="px-3 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} className="border-t border-zinc-800">
                  <td className="px-3 py-2 font-medium">{r.symbol}</td>
                  <td className="px-3 py-2 text-zinc-400">{r.market}</td>
                  <td className="px-3 py-2">{Number(r.gozlem_skoru).toFixed(1)}</td>
                  <td className="px-3 py-2">{r.volume_z ?? "-"}</td>
                  <td className="px-3 py-2">{r.rsi ?? "-"}</td>
                  <td className="px-3 py-2">{r.ma20_cross ? "evet" : "-"}</td>
                  <td className="px-3 py-2">{r.pct_from_52w ?? "-"}</td>
                  <td className="px-3 py-2 text-xs text-zinc-500">{tarih(r.computed_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-zinc-500">
          Henüz gözlem sinyali yok — eşikler bilinçli olarak sıkı (z≥3 + çift gösterge).
        </p>
      )}
    </div>
  );
}
