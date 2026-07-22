// Sistem sağlığı — 22 Temmuz 2026 Gemini kesintisinin 12+ saat fark
// edilmeden sürmesinden çıkarılan ders: hatalar mevcut try/except'lerde
// yutuluyordu, hiçbir yerde görünmüyordu. Kritik (seviye='kritik') olanlar
// aynı zamanda Telegram'a da gider (bkz. brain.sistemik_hata_kontrolu).
import { db } from "@/lib/supabase";
import { tarih } from "@/lib/labels";

export const dynamic = "force-dynamic";

export default async function HatalarPage() {
  const { data: hatalar } = await db().from("sistem_hatalari").select("*")
    .order("created_at", { ascending: false }).limit(100);

  const kritikSonuncu = hatalar?.find((h) => h.seviye === "kritik");

  return (
    <div className="space-y-4">
      <p className="text-xs text-zinc-500">
        Sistemdeki hataların kaydı — çoğu izole/beklenen (tek sembol/kaynak hatası,
        pipeline devam eder), &quot;kritik&quot; etiketli olanlar sistemik bir sorunu
        işaret eder ve Telegram&apos;a da gitmiştir.
      </p>

      {kritikSonuncu && (
        <div className="rounded-lg border border-red-800 bg-red-950 px-4 py-3">
          <p className="text-sm text-red-200 font-medium">
            ⚠️ En son kritik hata: {tarih(kritikSonuncu.created_at)}
          </p>
          <p className="text-sm text-red-300 mt-1">{kritikSonuncu.mesaj}</p>
        </div>
      )}

      {hatalar?.length ? (
        <ul className="space-y-2">
          {hatalar.map((h) => (
            <li key={h.id} className={`rounded-lg border px-4 py-3 ${
              h.seviye === "kritik" ? "border-red-900 bg-red-950/30" : "border-zinc-800 bg-zinc-900"
            }`}>
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-xs rounded px-2 py-0.5 bg-zinc-800 text-zinc-300">
                  {h.kaynak}
                </span>
                {h.seviye === "kritik" && (
                  <span className="text-xs rounded px-2 py-0.5 bg-red-900 text-red-200">
                    kritik
                  </span>
                )}
                <span className="ml-auto text-xs text-zinc-500">{tarih(h.created_at)}</span>
              </div>
              <p className="mt-1.5 text-sm text-zinc-300">{h.mesaj}</p>
              {h.detay && (
                <details className="mt-1">
                  <summary className="text-xs text-zinc-500 cursor-pointer hover:text-zinc-300">
                    detay
                  </summary>
                  <pre className="mt-1 text-xs text-zinc-500 whitespace-pre-wrap overflow-x-auto">
                    {h.detay}
                  </pre>
                </details>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-zinc-500">Kayıtlı hata yok.</p>
      )}
    </div>
  );
}
