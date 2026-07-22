// Ayarlar sayfası — pozisyon büyüklüğü ve tez açılış hurdle'ını etkileyen
// sayıları site üzerinden değiştirmeyi sağlar (önceden sadece Supabase'den
// elle mümkündü).
import { db } from "@/lib/supabase";
import { tarih } from "@/lib/labels";

export const dynamic = "force-dynamic";

const MESAJ: Record<string, { text: string; ok: boolean }> = {
  kaydedildi: { text: "Ayarlar kaydedildi.", ok: true },
  sayi: { text: "Sayısal alanlardan biri geçersiz.", ok: false },
  negatif: { text: "Sermaye alanları negatif olamaz.", ok: false },
  saat: { text: "Saat alanı SS:DD formatında olmalı (örn. 01:00).", ok: false },
  kayit: { text: "Kayıt sırasında hata oluştu, tekrar dene.", ok: false },
};

function Alan({ ad, etiket, aciklama, children }: {
  ad: string; etiket: string; aciklama?: string; children: React.ReactNode;
}) {
  return (
    <label className="text-sm text-zinc-300 space-y-1 block">
      <span className="font-medium">{etiket}</span>
      {aciklama && <span className="block text-xs text-zinc-500">{aciklama}</span>}
      {children}
    </label>
  );
}

export default async function AyarlarPage({
  searchParams,
}: {
  searchParams: Promise<{ ok?: string; hata?: string }>;
}) {
  const { ok, hata } = await searchParams;
  const mesaj = MESAJ[ok ?? hata ?? ""];

  const { data: s } = await db().from("user_settings").select("*").eq("id", 1).single();
  const input = "rounded border border-zinc-700 bg-zinc-800 px-2 py-1.5 text-sm w-full max-w-xs";

  return (
    <div className="space-y-5 max-w-2xl">
      {mesaj && (
        <p className={`rounded border px-3 py-2 text-sm ${
          mesaj.ok
            ? "border-emerald-800 bg-emerald-950 text-emerald-200"
            : "border-red-800 bg-red-950 text-red-200"
        }`}>
          {mesaj.text}
        </p>
      )}

      <form method="post" action="/api/ayarlar" className="space-y-6">
        <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 space-y-4">
          <h2 className="text-sm font-semibold text-zinc-400 uppercase">Sermaye ve risk</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <Alan ad="toplam_sermaye" etiket="Toplam sermaye"
              aciklama="Gerçek portföy için pozisyon büyüklüğü hesabının tabanı.">
              <input name="toplam_sermaye" type="number" step="any" min="0" className={input}
                defaultValue={s?.toplam_sermaye ?? ""} placeholder="örn. 100000" />
            </Alan>
            <Alan ad="deneme_sermaye" etiket="Deneme sermayesi"
              aciklama="Sanal — deneme portföyü için, gerçek toplamlara asla girmez.">
              <input name="deneme_sermaye" type="number" step="any" min="0" className={input}
                defaultValue={s?.deneme_sermaye ?? ""} placeholder="örn. 50000" />
            </Alan>
            <Alan ad="temel_risk_pct" etiket="Temel risk %"
              aciklama="Tek tezde riske atılacak sermaye yüzdesi (varsayılan 1.0).">
              <input name="temel_risk_pct" type="number" step="any" min="0" max="100" className={input}
                defaultValue={s?.temel_risk_pct ?? ""} />
            </Alan>
            <Alan ad="max_tek_pozisyon_pct" etiket="Tek pozisyon tavanı %"
              aciklama="Bir sembole sermayenin en fazla bu kadarı ayrılır (varsayılan 10).">
              <input name="max_tek_pozisyon_pct" type="number" step="any" min="0" max="100" className={input}
                defaultValue={s?.max_tek_pozisyon_pct ?? ""} />
            </Alan>
            <Alan ad="max_tema_pct" etiket="Tema tavanı %"
              aciklama="Aynı sektör/temada (örn. enerji) toplam maruziyet tavanı (varsayılan 15).">
              <input name="max_tema_pct" type="number" step="any" min="0" max="100" className={input}
                defaultValue={s?.max_tema_pct ?? ""} />
            </Alan>
          </div>
        </section>

        <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 space-y-4">
          <h2 className="text-sm font-semibold text-zinc-400 uppercase">Engel oranı (BIST)</h2>
          <p className="text-xs text-zinc-500">
            BIST tezleri için: tezin yıllık eşdeğer getirisi bu ikisinden yüksek olanı
            yenmiyorsa tez açılmaz (risksiz alternatif daha iyi demektir).
          </p>
          <div className="grid sm:grid-cols-2 gap-4">
            <Alan ad="enflasyon_yillik" etiket="Yıllık enflasyon %" aciklama="TÜİK yıllık TÜFE — ayda bir güncelle.">
              <input name="enflasyon_yillik" type="number" step="any" min="0" className={input}
                defaultValue={s?.enflasyon_yillik ?? ""} />
            </Alan>
            <Alan ad="mevduat_yillik" etiket="Yıllık mevduat faizi %" aciklama="Bankandaki güncel TL mevduat faizi.">
              <input name="mevduat_yillik" type="number" step="any" min="0" className={input}
                defaultValue={s?.mevduat_yillik ?? ""} />
            </Alan>
          </div>
        </section>

        <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 space-y-4">
          <h2 className="text-sm font-semibold text-zinc-400 uppercase">Bildirim</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <Alan ad="sessiz_saat_baslangic" etiket="Sessiz saat başlangıcı"
              aciklama="Bu aralıkta acil olmayan bildirimler sabaha ertelenir.">
              <input name="sessiz_saat_baslangic" type="time" className={input}
                defaultValue={s?.sessiz_saat_baslangic?.slice(0, 5) ?? "01:00"} />
            </Alan>
            <Alan ad="sessiz_saat_bitis" etiket="Sessiz saat bitişi">
              <input name="sessiz_saat_bitis" type="time" className={input}
                defaultValue={s?.sessiz_saat_bitis?.slice(0, 5) ?? "08:00"} />
            </Alan>
          </div>
          <label className="flex items-center gap-2 text-sm text-zinc-300">
            <input type="checkbox" name="gozlem_bolumu_aktif" value="1"
              defaultChecked={s?.gozlem_bolumu_aktif ?? true} />
            <span>Günlük raporda gözlem (teknik anomali) bölümünü göster</span>
          </label>
        </section>

        <button type="submit"
          className="rounded bg-emerald-700 hover:bg-emerald-600 px-4 py-1.5 text-sm font-medium">
          Kaydet
        </button>
      </form>

      {s?.updated_at && (
        <p className="text-xs text-zinc-600">Son güncelleme: {tarih(s.updated_at)}</p>
      )}
    </div>
  );
}
