// Faz 12 B — ikinci derece akıl yürütmenin füzyon şartını geçemeyen bağları.
// Tez değildir, bildirim gitmez; teknik kurulunca (main.py her koşuda kontrol
// eder) teze döner, süresi dolarsa düşer.
import Link from "next/link";
import { db } from "@/lib/supabase";
import { GUVEN, YON, tarih } from "@/lib/labels";

export const dynamic = "force-dynamic";

const DURUM_IZLEME: Record<string, { label: string; cls: string }> = {
  bekliyor: { label: "bekliyor", cls: "bg-amber-900 text-amber-200" },
  teyit_edildi: { label: "teyit edildi → tez oldu", cls: "bg-emerald-900 text-emerald-200" },
  suresi_doldu: { label: "süresi doldu", cls: "bg-zinc-700 text-zinc-300" },
};

export default async function IzlemePage() {
  const { data: rows } = await db().from("ikinci_derece_izleme")
    .select("*").order("created_at", { ascending: false }).limit(50);

  return (
    <div className="space-y-4">
      <p className="text-xs text-zinc-500">
        Sistem çok kaynaklı ama hiçbir sembole doğrudan bağlanamayan haberler için
        ikinci derece (dolaylı) bir bağ kurdu, ama grafikte henüz teknik destek yok
        — bu yüzden tez açılmadı. Teknik kurulum oluşursa otomatik teze döner.
      </p>
      {rows?.length ? (
        <ul className="space-y-2">
          {rows.map((r) => (
            <li key={r.id} className="rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-3">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="font-medium">{r.symbol}</span>
                <span className="text-xs text-zinc-500">{r.market}</span>
                <span className="text-xs text-zinc-400">{YON[r.yon] ?? r.yon}</span>
                <span className="text-xs text-zinc-500">güven: {GUVEN[r.guven] ?? r.guven}</span>
                <span className={`text-xs rounded px-2 py-0.5 ${DURUM_IZLEME[r.status]?.cls ?? ""}`}>
                  {DURUM_IZLEME[r.status]?.label ?? r.status}
                </span>
                <span className="ml-auto text-xs text-zinc-500">{tarih(r.created_at)}</span>
              </div>
              <p className="mt-1 text-sm text-zinc-300">{r.mekanizma}</p>
              {r.kaynak_baslik && (
                <p className="mt-1 text-xs text-zinc-500">
                  Kaynak haber: {r.kaynak_url ? (
                    <a href={r.kaynak_url} target="_blank" rel="noopener noreferrer"
                      className="text-blue-400 hover:underline">{r.kaynak_baslik}</a>
                  ) : r.kaynak_baslik}
                </p>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-zinc-500">İzlemede bekleyen bağ yok.</p>
      )}
      <p className="text-xs text-zinc-600">
        Teze dönenler <Link href="/tezler?kaynak=ikinci_derece" className="hover:underline text-zinc-400">
          tezler listesinde &quot;ikinci derece&quot; kaynağıyla
        </Link> görünür.
      </p>
    </div>
  );
}
