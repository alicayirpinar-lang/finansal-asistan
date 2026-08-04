// Getiri metrikleri (plan 7.4) — kullanıcının asıl hedefi olan "%20 yıllık"ı
// dürüstçe ölçen sayfa. Veri, rapor turlarında Python'un yazdığı
// portfolio_metrics anlık görüntülerinden gelir (canlı hesap yok).
import { db } from "@/lib/supabase";
import { tarih } from "@/lib/labels";

export const dynamic = "force-dynamic";

/* eslint-disable @typescript-eslint/no-explicit-any */

async function metrikGecmisi(): Promise<Record<string, any[]>> {
  // 31 Temmuz 2026: eskiden sadece EN SON anlık görüntü tutuluyordu — rapor/
  // takip turlarında günde ~4 kez yazılan geçmiş hiç kullanılmıyordu. Artık
  // tüm geçmiş çekilip getiri eğrisi (Sparkline) için kullanılıyor.
  const { data } = await db().from("portfolio_metrics")
    .select("scope,metrics,computed_at")
    .order("computed_at", { ascending: true }).limit(500);
  const out: Record<string, any[]> = {};
  for (const row of data ?? []) {
    (out[row.scope] ??= []).push(row);
  }
  return out;
}

function Sparkline({ degerler }: { degerler: number[] }) {
  if (degerler.length < 2) return null;
  const w = 200, h = 32, pad = 2;
  const min = Math.min(...degerler, 0), max = Math.max(...degerler, 0);
  const aralik = max - min || 1;
  const noktalar = degerler.map((v, i) => {
    const x = pad + (i / (degerler.length - 1)) * (w - 2 * pad);
    const y = h - pad - ((v - min) / aralik) * (h - 2 * pad);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const sifirY = h - pad - ((0 - min) / aralik) * (h - 2 * pad);
  const son = degerler[degerler.length - 1];
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-8 mt-1" preserveAspectRatio="none">
      <line x1={0} y1={sifirY} x2={w} y2={sifirY} stroke="#3f3f46" strokeWidth={1} strokeDasharray="3,3" />
      <polyline points={noktalar} fill="none" strokeWidth={1.5}
        stroke={son >= 0 ? "#34d399" : "#f87171"} />
    </svg>
  );
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

function PortfoyKarti({ baslik, gecmis, uyari }: { baslik: string; gecmis: any[]; uyari?: string }) {
  const row = gecmis.at(-1);
  const egriDegerleri = gecmis
    .map((r) => r.metrics.toplam_getiri_pct)
    .filter((v: any) => v !== null && v !== undefined);
  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
      <h2 className="text-sm font-semibold text-zinc-400 uppercase mb-1">{baslik}</h2>
      {uyari && <p className="text-xs text-zinc-500 mb-2">{uyari}</p>}
      {row ? (
        <>
          <Satir ad="Toplam getiri"><Pct v={row.metrics.toplam_getiri_pct} /></Satir>
          <Sparkline degerler={egriDegerleri} />
          {egriDegerleri.length >= 2 && (
            <p className="text-[10px] text-zinc-600 mb-1">
              son {egriDegerleri.length} ölçüm — getiri eğrisi (rapor/takip turlarında kaydedilir)
            </p>
          )}
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

const KAYNAK_ADI: Record<string, string> = {
  haber: "Haber", teknik: "Teknik radar", ikinci_derece: "İkinci derece", geriye_donuk: "Geriye dönük",
};
const GUVEN_ADI: Record<string, string> = { dusuk: "Düşük", orta: "Orta", yuksek: "Yüksek" };

function SegmentTablosu({ segmentler }: { segmentler: any[] }) {
  if (!segmentler?.length) return null;
  return (
    <div className="mt-3 overflow-x-auto">
      <p className="text-xs text-zinc-500 mb-1">
        Kaynak × güven kırılımı — harmanlanmış tek sayı, hiç önerilmemiş (düşük güven)
        tezlerin gerçek bildirim giden (orta/kritik) tezlerin performansını gizlemesini önler.
      </p>
      <table className="w-full text-sm">
        <thead className="text-zinc-500 text-xs uppercase">
          <tr>
            {["Kaynak", "Güven", "N", "İsabet", "Ort. kazanç", "Ort. kayıp", "Expectancy"].map((h) => (
              <th key={h} className="px-2 py-1 text-left font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {segmentler.map((s, i) => (
            <tr key={i} className="border-t border-zinc-800">
              <td className="px-2 py-1 text-zinc-300">{KAYNAK_ADI[s.kaynak] ?? s.kaynak}</td>
              <td className="px-2 py-1 text-zinc-300">{GUVEN_ADI[s.final_confidence] ?? s.final_confidence}</td>
              <td className="px-2 py-1 text-zinc-400">{s.n}</td>
              <td className="px-2 py-1 font-medium">%{Math.round(s.isabet_orani * 100)}</td>
              <td className="px-2 py-1"><Pct v={s.ort_kazanc_pct} /></td>
              <td className="px-2 py-1"><Pct v={-s.ort_kayip_pct} /></td>
              <td className="px-2 py-1"><Pct v={s.expectancy_pct} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TezKarti({ row, dogrulanmisSayisi }: { row?: any; dogrulanmisSayisi: number }) {
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
          <SegmentTablosu segmentler={m.segmentler} />
          {dogrulanmisSayisi > 0 && (
            <p className="text-xs text-sky-400 mt-3">
              ✓ {dogrulanmisSayisi} tez birden fazla kaynaktan doğrulandı (aynı olay farklı
              haberlerde de görüldü — mükerrer tez açılmadı, tek teze toplandı).
            </p>
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

async function dogrulanmisTezSayisi(): Promise<number> {
  const { count } = await db().from("theses")
    .select("id", { count: "exact", head: true }).gt("dogrulama_sayisi", 0);
  return count ?? 0;
}

export default async function GetiriPage() {
  const [gecmis, dogrulanmisSayisi] = await Promise.all([
    metrikGecmisi(), dogrulanmisTezSayisi(),
  ]);
  return (
    <div className="space-y-5">
      <p className="text-xs text-zinc-500">
        Bu sayfa &quot;sistemi takip etseydim ne kazandırırdı?&quot; sorusunu ölçer.
        Benchmark satırları dürüstlük kontrolüdür: portföy endeksi geçemiyorsa
        endeks fonu daha zahmetsiz demektir. Veriler rapor saatlerinde güncellenir.
      </p>
      <PortfoyKarti baslik="Gerçek portföy" gecmis={gecmis.gercek ?? []} />
      <PortfoyKarti baslik="Deneme portföyü" gecmis={gecmis.deneme ?? []}
        uyari="Sanal — gerçek para değildir, gerçek toplamlara asla dahil edilmez." />
      <TezKarti row={gecmis.tezler?.at(-1)} dogrulanmisSayisi={dogrulanmisSayisi} />
    </div>
  );
}
