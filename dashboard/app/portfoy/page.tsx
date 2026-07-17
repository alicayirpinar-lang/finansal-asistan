import Link from "next/link";
import { db } from "@/lib/supabase";
import KapatButton from "./KapatButton";

export const dynamic = "force-dynamic";

/* eslint-disable @typescript-eslint/no-explicit-any */

const MESAJ: Record<string, { text: string; ok: boolean }> = {
  eklendi: { text: "Pozisyon eklendi.", ok: true },
  eklendi_retro: {
    text: "Pozisyon eklendi; geriye dönük tez talebi kuyruğa alındı — sonraki tarama turunda (en geç ~30 dk) işlenir, sonuç Telegram'a gelir.",
    ok: true,
  },
  kapatildi: { text: "Pozisyon kapatıldı. Bağlı tez varsa 'kullanıcı sattı' olarak işaretlendi.", ok: true },
  sembol: { text: "Sembol geçersiz (örn. THYAO, NVDA — en fazla 10 karakter).", ok: false },
  pazar: { text: "Pazar seçilmedi.", ok: false },
  adet: { text: "Adet 0'dan büyük bir sayı olmalı.", ok: false },
  fiyat: { text: "Alış fiyatı 0'dan büyük bir sayı olmalı.", ok: false },
  tarih: { text: "Tarih geçersiz (gelecek tarih olamaz).", ok: false },
  tur: { text: "Gerçek / Deneme seçimi zorunlu (varsayılan yok — bilinçli seçim).", ok: false },
  kayit: { text: "Kayıt sırasında hata oluştu, tekrar dene.", ok: false },
  kapat: { text: "Pozisyon kapatılamadı (bulunamadı veya zaten kapalı).", ok: false },
  kapatfiyat: { text: "Satış fiyatı geçersiz — sayı gir veya boş bırak.", ok: false },
};

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
                <KapatButton id={p.id} symbol={p.symbol} />
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

function EkleFormu({ acikTezler }: { acikTezler: any[] }) {
  const input = "rounded border border-zinc-700 bg-zinc-800 px-2 py-1.5 text-sm w-full";
  const bugun = new Date().toISOString().slice(0, 10);
  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
      <h2 className="text-sm font-semibold text-zinc-400 uppercase mb-3">Pozisyon ekle</h2>
      <form method="post" action="/api/pozisyon" className="space-y-3">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <label className="text-xs text-zinc-400 space-y-1">
            <span>Sembol</span>
            <input name="sembol" required placeholder="THYAO / NVDA"
              className={`${input} uppercase`} maxLength={10} />
          </label>
          <label className="text-xs text-zinc-400 space-y-1">
            <span>Adet</span>
            <input name="adet" required type="number" step="any" min="0.0001"
              placeholder="10" className={input} />
          </label>
          <label className="text-xs text-zinc-400 space-y-1">
            <span>Alış fiyatı</span>
            <input name="fiyat" required type="number" step="any" min="0.0001"
              placeholder="330.50" className={input} />
          </label>
          <label className="text-xs text-zinc-400 space-y-1">
            <span>Alış tarihi</span>
            <input name="tarih" required type="date" defaultValue={bugun} max={bugun}
              className={input} />
          </label>
        </div>

        <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
          <fieldset className="flex items-center gap-3">
            <legend className="sr-only">Pazar</legend>
            <span className="text-xs text-zinc-400">Pazar:</span>
            <label className="flex items-center gap-1">
              <input type="radio" name="pazar" value="BIST" required /> BIST
            </label>
            <label className="flex items-center gap-1">
              <input type="radio" name="pazar" value="US" required /> ABD
            </label>
          </fieldset>
          <fieldset className="flex items-center gap-3">
            <legend className="sr-only">Portföy türü</legend>
            <span className="text-xs text-zinc-400">Portföy:</span>
            <label className="flex items-center gap-1">
              <input type="radio" name="tur" value="gercek" required /> Gerçek
            </label>
            <label className="flex items-center gap-1">
              <input type="radio" name="tur" value="deneme" required /> Deneme
            </label>
          </fieldset>
        </div>

        <div className="grid sm:grid-cols-2 gap-3 items-end">
          <label className="text-xs text-zinc-400 space-y-1 block">
            <span>Sistem tezine bağla (opsiyonel)</span>
            <select name="tez" className={input} defaultValue="">
              <option value="">— tez yok (dışarıdan alım) —</option>
              {acikTezler.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.symbol} · {t.direction === "yukselis" ? "↑" : "↓"} · güven: {t.final_confidence}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-zinc-300">
            <input type="checkbox" name="retro" value="1" />
            <span>Tez seçmediysem <b>geriye dönük tez</b> kurulsun (AI son haberlerden gerekçe arar)</span>
          </label>
        </div>

        <button type="submit"
          className="rounded bg-emerald-700 hover:bg-emerald-600 px-4 py-1.5 text-sm font-medium">
          Ekle
        </button>
      </form>
    </section>
  );
}

export default async function PortfoyPage({
  searchParams,
}: {
  searchParams: Promise<{ ok?: string; hata?: string }>;
}) {
  const { ok, hata } = await searchParams;
  const mesaj = MESAJ[ok ?? hata ?? ""];

  const [{ data: rows }, { data: tezRows }] = await Promise.all([
    db().from("portfolio").select("*")
      .eq("status", "acik").order("entry_date", { ascending: false }),
    db().from("theses").select("id,symbol,direction,final_confidence")
      .eq("status", "acik").order("created_at", { ascending: false }).limit(50),
  ]);
  const positions = rows ?? [];
  const fiyatlar = await sonFiyatlar([...new Set(positions.map((p) => p.symbol))]);

  return (
    <div className="space-y-5">
      {mesaj && (
        <p className={`rounded border px-3 py-2 text-sm ${
          mesaj.ok
            ? "border-emerald-800 bg-emerald-950 text-emerald-200"
            : "border-red-800 bg-red-950 text-red-200"
        }`}>
          {mesaj.text}
        </p>
      )}
      <Grup baslik="Gerçek portföy" fiyatlar={fiyatlar}
        rows={positions.filter((p) => p.portfolio_type === "gercek")} />
      <Grup baslik="Deneme portföyü" fiyatlar={fiyatlar}
        rows={positions.filter((p) => p.portfolio_type === "deneme")}
        uyari="Sanal — gerçek para değildir, gerçek toplamlara asla dahil edilmez." />
      <EkleFormu acikTezler={tezRows ?? []} />
      <p className="text-xs text-zinc-500">
        Fiyatlar son takip turundan alınır (canlı değildir). Kısmi kapama için
        bilgisayardaki manage.py kullanılır.
      </p>
    </div>
  );
}
