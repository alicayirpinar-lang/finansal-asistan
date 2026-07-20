import { db } from "@/lib/supabase";
import { guncelFiyat } from "@/lib/fiyat";
import { DURUM, GUVEN, KATALIZOR, KURULUM, REJIM, YON, tarih } from "@/lib/labels";

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
  const tg: any = draft.teknik_gorunum ?? null; // faz 11 öncesi tezlerde yok

  const [{ data: checks }, canli] = await Promise.all([
    db().from("thesis_checks")
      .select("checked_at,price_at_check,result")
      .eq("thesis_id", id).order("checked_at", { ascending: false }).limit(10),
    guncelFiyat(t.symbol, t.market),
  ]);

  const ref = t.entry_price_ref ? Number(t.entry_price_ref) : null;
  const refFark = canli && ref ? ((canli.fiyat - ref) / ref) * 100 : null;

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-2xl font-semibold">{t.symbol}</h1>
        <span className="text-sm text-zinc-500">{t.market}</span>
        <span className="text-sm text-zinc-300">{YON[t.direction] ?? t.direction}</span>
        <span className={`text-xs rounded px-2 py-0.5 ${DURUM[t.status]?.cls ?? ""}`}>
          {DURUM[t.status]?.label ?? t.status}
        </span>
        {tg?.buyuk_firsat ? (
          <span className="text-xs rounded px-2 py-0.5 bg-amber-900 text-amber-200">
            🚀 büyük fırsat adayı
          </span>
        ) : null}
        <span className="ml-auto text-xs text-zinc-500">{tarih(t.created_at)}</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 text-sm">
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
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-3">
          <div className="text-xs text-zinc-500">Güncel fiyat</div>
          {canli ? (
            <>
              <div className="mt-0.5">
                {canli.fiyat}
                {refFark !== null && (
                  <span className={`ml-2 text-xs ${refFark >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                    referanstan %{refFark >= 0 ? "+" : ""}{refFark.toFixed(1)}
                  </span>
                )}
              </div>
              <div className="text-[10px] text-zinc-600 mt-0.5">
                {canli.zaman ? `son işlem ${tarih(canli.zaman.toISOString())} · ` : ""}~5 dk önbellek
              </div>
            </>
          ) : (
            <div className="mt-0.5 text-zinc-500 text-xs">şu an alınamadı</div>
          )}
        </div>
      </div>

      {tg ? (
        <Kutu baslik="Teknik görünüm (matematiksel analiz)">
          <div className="space-y-3">
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
              <span>
                <span className="text-xs text-zinc-500">piyasa rejimi: </span>
                <span className={REJIM[tg.rejim]?.cls ?? "text-zinc-300"}>
                  {REJIM[tg.rejim]?.label ?? tg.rejim ?? "-"}
                </span>
              </span>
              <span>
                <span className="text-xs text-zinc-500">katalizör türü: </span>
                {KATALIZOR[tg.katalizor] ?? tg.katalizor ?? "-"}
              </span>
              {tg.tepki?.gun_getiri_pct != null && (
                <span>
                  <span className="text-xs text-zinc-500">olay günü tepkisi: </span>
                  fiyat %{tg.tepki.gun_getiri_pct >= 0 ? "+" : ""}{tg.tepki.gun_getiri_pct}
                  {tg.tepki.hacim_kati != null ? `, hacim normalin ${tg.tepki.hacim_kati} katı` : ""}
                </span>
              )}
            </div>

            {tg.kurulumlar?.length ? (
              <ul className="space-y-2">
                {tg.kurulumlar.map((k: any) => (
                  <li key={k.ad} className="border-l-2 border-zinc-700 pl-3">
                    <div className="flex items-center gap-2 flex-wrap text-sm">
                      <span className="font-medium">{KURULUM[k.ad] ?? k.ad}</span>
                      <span className="text-xs text-zinc-500">
                        {YON[k.yon] ?? k.yon} · skor {k.skor}
                      </span>
                      <span className={`text-[10px] rounded px-1.5 py-0.5 ${
                        k.kanitli
                          ? "bg-emerald-900 text-emerald-200"
                          : "bg-zinc-800 text-zinc-400"
                      }`}>
                        {k.kanitli ? "backtest kanıtlı" : "kanıt yok — bağlamsal bilgi"}
                      </span>
                    </div>
                    {k.kosullar?.length ? (
                      <div className="text-xs text-zinc-500 mt-0.5">{k.kosullar.join(" · ")}</div>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-zinc-500">Kurulum yok (nötr grafik).</p>
            )}

            {tg.engel ? <p className="text-xs text-amber-300">{tg.engel}</p> : null}
            <p className="text-[10px] text-zinc-600">
              Bu bölüm tamamen kod ile hesaplanır (AI üretmez, yorumlar) — göstergeler, kurulum
              tespiti ve rejim tez anındaki verilerden çıkarılmıştır.
            </p>
          </div>
        </Kutu>
      ) : null}

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
          {rt.onemlilik && (
            <Soru q="Olay gerçekten önemli mi?">
              {rt.onemlilik.onemli_mi ? "evet" : "hayır"} — {rt.onemlilik.aciklama ?? ""}
            </Soru>
          )}
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
