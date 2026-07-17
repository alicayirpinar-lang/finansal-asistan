import { db } from "@/lib/supabase";
import { DURUM, GUVEN, YON, tarih } from "@/lib/labels";

export const dynamic = "force-dynamic";

/* eslint-disable @typescript-eslint/no-explicit-any */

function Kutu({ baslik, children }: { baslik: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
      <h2 className="text-sm font-semibold text-zinc-400 uppercase mb-3">{baslik}</h2>
      {children}
    </section>
  );
}

function Soru({ q, children }: { q: string; children: React.ReactNode }) {
  return (
    <div className="border-l-2 border-zinc-700 pl-3">
      <div className="text-xs text-zinc-500">{q}</div>
      <div className="text-sm text-zinc-200 mt-0.5">{children}</div>
    </div>
  );
}

export default async function TezDetayPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { data: t } = await db().from("theses").select("*").eq("id", id).single();
  if (!t) return <p className="text-sm text-zinc-500">Tez bulunamadı.</p>;

  const draft: any = t.draft_chain ?? {};
  const rt: any = t.redteam_output ?? {};
  const inv: any = t.invalidation_condition ?? {};

  const { data: checks } = await db().from("thesis_checks")
    .select("checked_at,price_at_check,result")
    .eq("thesis_id", id).order("checked_at", { ascending: false }).limit(10);

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-2xl font-semibold">{t.symbol}</h1>
        <span className="text-sm text-zinc-500">{t.market}</span>
        <span className="text-sm text-zinc-300">{YON[t.direction] ?? t.direction}</span>
        <span className={`text-xs rounded px-2 py-0.5 ${DURUM[t.status]?.cls ?? ""}`}>
          {DURUM[t.status]?.label ?? t.status}
        </span>
        <span className="ml-auto text-xs text-zinc-500">{tarih(t.created_at)}</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        {[
          ["Güven", GUVEN[t.final_confidence] ?? "-"],
          ["Hedef", String(t.target_range_pct ?? "-") + " %"],
          ["Ufuk", t.horizon ?? "-"],
          ["Referans fiyat", t.entry_price_ref ?? "-"],
        ].map(([k, v]) => (
          <div key={k as string} className="rounded-lg border border-zinc-800 bg-zinc-900 p-3">
            <div className="text-xs text-zinc-500">{k}</div>
            <div className="mt-0.5">{v as string}</div>
          </div>
        ))}
      </div>

      <Kutu baslik="Sebep-sonuç zinciri">
        <ol className="space-y-2">
          {(draft.zincir ?? []).map((a: any) => (
            <li key={a.adim_no} className="flex gap-3">
              <span className="text-emerald-400 font-mono text-sm">{a.adim_no}.</span>
              <div>
                <div className="text-sm">{a.mekanizma}</div>
                <div className="text-xs text-zinc-500 mt-0.5">
                  güven: {GUVEN[a.guven] ?? a.guven} · dayanak: {a.dayanak}
                </div>
              </div>
            </li>
          ))}
        </ol>
      </Kutu>

      <Kutu baslik="Kendini eleştiri (red-team)">
        <div className="space-y-3">
          <Soru q="En zayıf halka">{rt.en_zayif_halka?.aciklama ?? "-"}</Soru>
          <Soru q="Zaten fiyatlanmış mı?">
            {rt.zaten_fiyatlanmis_mi?.cevap ?? "-"} — {rt.zaten_fiyatlanmis_mi?.kanit ?? ""}
          </Soru>
          <Soru q="Alternatif açıklama">{rt.alternatif_aciklama?.aciklama ?? "-"}</Soru>
          <Soru q="Taban oranı">
            {rt.taban_orani?.kaynak === "veri yok"
              ? "veri yok"
              : `${rt.taban_orani?.basari_orani_pct ?? "?"}% (${rt.taban_orani?.vaka_sayisi ?? "?"} vaka, ${rt.taban_orani?.kaynak ?? ""})`}
          </Soru>
          <Soru q="Büyüklük tutarlı mı?">
            {rt.buyukluk_tutarliligi?.tutarli_mi ? "evet" : "hayır"} — {rt.buyukluk_tutarliligi?.aciklama ?? ""}
          </Soru>
          <Soru q="Zamanlama makul mü?">
            {rt.zamanlama_makul_mu?.makul_mu ? "evet" : "hayır"} — {rt.zamanlama_makul_mu?.aciklama ?? ""}
          </Soru>
          <Soru q="Kalabalık ticaret mi?">
            {rt.kalabalik_ticaret_mi?.evet_mi ? "evet" : "hayır"} — {rt.kalabalik_ticaret_mi?.kanit ?? ""}
          </Soru>
          {rt.guven_dusurme_gerekcesi && (
            <Soru q="Güven düşürme gerekçesi">{rt.guven_dusurme_gerekcesi}</Soru>
          )}
        </div>
      </Kutu>

      <Kutu baslik="Geçersiz kılma koşulu">
        <p className="text-sm">{inv.kosul ?? "-"}</p>
        <p className="text-xs text-zinc-500 mt-1">
          izleme: {inv.izleme_yontemi ?? "-"}
          {inv.stop_fiyat ? ` · stop fiyat: ${inv.stop_fiyat}` : ""}
        </p>
        {inv.zayif_sinyal_kelimeleri?.length ? (
          <p className="text-xs text-zinc-500 mt-1">
            zayıf sinyaller: {inv.zayif_sinyal_kelimeleri.join(", ")}
          </p>
        ) : null}
      </Kutu>

      {checks?.length ? (
        <Kutu baslik="Takip geçmişi">
          <ul className="space-y-1 text-sm">
            {checks.map((c, i) => (
              <li key={i} className="flex gap-3 text-zinc-300">
                <span className="text-xs text-zinc-500 w-32 shrink-0">{tarih(c.checked_at)}</span>
                <span className="w-20 shrink-0">{c.price_at_check ?? "-"}</span>
                <span className="text-zinc-400">{c.result}</span>
              </li>
            ))}
          </ul>
        </Kutu>
      ) : null}

      {t.resolution_note && (
        <p className="text-sm text-zinc-400">Sonuç notu: {t.resolution_note}</p>
      )}
    </div>
  );
}
