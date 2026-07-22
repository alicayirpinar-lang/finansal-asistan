import Link from "next/link";
import { db } from "@/lib/supabase";
import { DURUM, MESAJ_TUR, tarih } from "@/lib/labels";

export const dynamic = "force-dynamic";

export default async function OzetPage() {
  const client = db();
  const dun = new Date(Date.now() - 24 * 3600 * 1000).toISOString();

  const [acikTez, sonTezler, pozisyonlar, sonAlertler] = await Promise.all([
    client.from("theses").select("id", { count: "exact", head: true }).eq("status", "acik"),
    client.from("theses").select("id,symbol,market,status,final_confidence,created_at")
      .gte("created_at", dun).neq("status", "iptal_edildi")
      .order("created_at", { ascending: false }).limit(8),
    client.from("portfolio").select("id,portfolio_type").eq("status", "acik"),
    client.from("mesaj_log").select("tur,icerik,basarili,created_at")
      .order("created_at", { ascending: false }).limit(5),
  ]);

  const gercek = (pozisyonlar.data ?? []).filter((p) => p.portfolio_type === "gercek").length;
  const deneme = (pozisyonlar.data ?? []).filter((p) => p.portfolio_type === "deneme").length;

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { k: "Açık tez", v: acikTez.count ?? 0 },
          { k: "Son 24s yeni tez", v: sonTezler.data?.length ?? 0 },
          { k: "Gerçek pozisyon", v: gercek },
          { k: "Deneme pozisyon", v: deneme },
        ].map((c) => (
          <div key={c.k} className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <div className="text-2xl font-semibold">{c.v}</div>
            <div className="text-xs text-zinc-400 mt-1">{c.k}</div>
          </div>
        ))}
      </div>

      <section>
        <h2 className="text-sm font-semibold text-zinc-400 uppercase mb-3">Son 24 saatin tezleri</h2>
        {sonTezler.data?.length ? (
          <ul className="space-y-2">
            {sonTezler.data.map((t) => (
              <li key={t.id}>
                <Link href={`/tez/${t.id}`}
                  className="flex items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-3 hover:border-zinc-600">
                  <span className="font-medium w-16">{t.symbol}</span>
                  <span className="text-xs text-zinc-500 w-10">{t.market}</span>
                  <span className={`text-xs rounded px-2 py-0.5 ${DURUM[t.status]?.cls ?? ""}`}>
                    {DURUM[t.status]?.label ?? t.status}
                  </span>
                  <span className="ml-auto text-xs text-zinc-500">{tarih(t.created_at)}</span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-zinc-500">Son 24 saatte yeni tez yok.</p>
        )}
      </section>

      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-zinc-400 uppercase">Son mesajlar</h2>
          <Link href="/bildirimler" className="text-xs text-blue-400 hover:underline">
            tümünü gör →
          </Link>
        </div>
        {sonAlertler.data?.length ? (
          <ul className="space-y-1 text-sm">
            {sonAlertler.data.map((a, i) => (
              <li key={i} className={a.basarili ? "text-zinc-300" : "text-red-400"}>
                <span className="text-zinc-500 text-xs mr-2">{tarih(a.created_at)}</span>
                <span className="text-zinc-500 text-xs mr-2">[{MESAJ_TUR[a.tur] ?? a.tur}]</span>
                {a.icerik?.split("\n")[0]}
                {!a.basarili && " — gönderilemedi"}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-zinc-500">Henüz mesaj yok.</p>
        )}
      </section>
    </div>
  );
}
