// Getiri metrikleri (plan 7.4) — kullanıcının asıl hedefi olan "%20 yıllık"ı
// dürüstçe ölçen sayfa. Veri, rapor turlarında Python'un yazdığı
// portfolio_metrics anlık görüntülerinden gelir (canlı hesap yok).
import { db } from "@/lib/supabase";
import { tarih } from "@/lib/labels";

export const dynamic = "force-dynamic";

/* eslint-disable @typescript-eslint/no-explicit-any */

async function sonMetrikler(): Promise<Record<string, any>> {
  const { data } = await db().from("portfolio_metrics")
    .select("scope,metrics,computed_at")
    .order("computed_at", { ascending: false }).limit(30);
  const out: Record<string, any> = {};
  for (const row of data ?? []) {
    if (!(row.scope in out)) out[row.scope] = row;
  }
  return out;
}

function Pct({ v, iyi }: { v: number | null | undefined; iyi?: boolean }) {
  if (v === null || v === undefined) return <span className="text-zinc-500">—</span>;
  const pozitifIyi = iyi ?? true;
  const renk = (v >= 0) === pozitifIyi ? "text-emerald-400" : "text-red-400";
  return <span className={renk}>%{v >= 0 ? "+" : ""}{v}</span>;
}

function Satir({ ad, children }: { ad: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 text-sm py-1">
      <span className="text-zinc-400">{ad}</span>
      <span className="font-medium">{children}</span>
    </div>
  );
}

function Notlar({ notlar }: { notlar?: string[] }) {
  if (!notlar?.length) return null;
  return (
    <ul className="mt-2 space-y-0.5">
      {notlar.map((n, i) => (
        <li key={i} className="text-xs text-amber-500/80">⚠ {n}</li>
      ))}
    </ul>
  );
}

function PortfoyKarti({ baslik, row, uyari }: { baslik: string; row?: any; uyari?: string }) {
  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
      <h2 className="text-sm font-semibold text-zinc-400 uppercase mb-1">{baslik}</h2>
      {uyari && <p className="text-xs text-zinc-500 mb-2">{uyari}</p>}
      {row ? (
        <>
          <Satir ad="Toplam getiri"><Pct v={row.metrics.toplam_getiri_pct} /></Satir>
          <Satir ad="Yıllıklandırılmış (XIRR)"><Pct v={row.metrics.xirr_pct} /></Satir>
          <Satir ad="Aynı dönemde BIST100">
            <Pct v={row.metrics.benchmark_pct?.BIST100} />
          </Satir>
          <Satir ad="Aynı dönemde S&P500">
            <Pct v={row.metrics.benchmark_pct?.["S&P500"]} />
          </Satir>
          <div className="border-t border-zinc-800 my-2" />
          <Satir ad="Yatırılan">{row.metrics.yatirilan}</Satir>
          <Satir ad="Açık pozisyon değeri">{row.metrics.acik_deger}</Satir>
          <Satir ad="Gerçekleşen (satışlardan dönen)">{row.metrics.gerceklesen}</Satir>
          <Satir ad="Pozisyon (açık / kapalı)">
            {row.metrics.acik_pozisyon} / {row.metrics.kapali_pozisyon}
          </Satir>
          <Satir ad="Takip süresi">{row.metrics.gun} gün ({row.metrics.baslangic}'ten beri)</Satir>
          <Notlar notlar={row.metrics.notlar} />
          <p className="text-xs text-zinc-600 mt-2">Son hesaplama: {tarih(row.computed_at)}</p>
        </>
      ) : (
        <p className="text-sm text-zinc-500">
          Henüz veri yok — bu portföye pozisyon girildikten sonraki ilk günlük raporda oluşur.
        </p>
      )}
    </section>
  );
}

function TezKarti({ row }: { row?: any }) {
  const m = row?.metrics;
  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
      <h2 className="text-sm font-semibold text-zinc-400 uppercase mb-1">Tez performansı (expectancy)</h2>
      <p className="text-xs text-zinc-500 mb-2">
        Portföyden bağımsız — sistemin ürettiği ve sonuca ulaşan tezlerin ölçüsüdür.
      </p>
      {m ? (
        <>
          <Satir ad="Çözülmüş tez">{m.cozulmus_tez}</Satir>
          {m.expectancy_pct !== undefined && (
            <>
              <Satir ad="İsabet oranı">%{Math.round(m.isabet_orani * 100)}</Satir>
              <Satir ad="Ortalama kazanç"><Pct v={m.ort_kazanc_pct} /></Satir>
              <Satir ad="Ortalama kayıp"><Pct v={-m.ort_kayip_pct} /></Satir>
              <Satir ad="Expectancy (tez başına beklenen)"><Pct v={m.expectancy_pct} /></Satir>
              <p className="text-xs text-zinc-500 mt-2">
                Expectancy pozitifse sistem, isabet oranı düşük olsa bile uzun vadede
                kazandırıyor demektir (asimetrik risk/ödül sayesinde).
              </p>
            </>
          )}
          <Notlar notlar={m.notlar} />
          <p className="text-xs text-zinc-600 mt-2">Son hesaplama: {tarih(row.computed_at)}</p>
        </>
      ) : (
        <p className="text-sm text-zinc-500">
          Henüz veri yok — ilk günlük raporla birlikte oluşur.
        </p>
      )}
    </section>
  );
}

export default async function GetiriPage() {
  const m = await sonMetrikler();
  return (
    <div className="space-y-5">
      <p className="text-xs text-zinc-500">
        Bu sayfa &quot;sistemi takip etseydim ne kazandırırdı?&quot; sorusunu ölçer.
        Benchmark satırları dürüstlük kontrolüdür: portföy endeksi geçemiyorsa
        endeks fonu daha zahmetsiz demektir. Veriler rapor saatlerinde güncellenir.
      </p>
      <PortfoyKarti baslik="Gerçek portföy" row={m.gercek} />
      <PortfoyKarti baslik="Deneme portföyü" row={m.deneme}
        uyari="Sanal — gerçek para değildir, gerçek toplamlara asla dahil edilmez." />
      <TezKarti row={m.tezler} />
    </div>
  );
}
