// Ayarlar formu — tek satırlık user_settings tablosunu günceller (id=1).
// Boş bırakılan sayısal alanlar null yazılır (o kısıt/özellik devre dışı kalır).
import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/supabase";

function geri(request: NextRequest, param: string) {
  return NextResponse.redirect(new URL(`/ayarlar?${param}`, request.url), 303);
}

function sayi(form: FormData, ad: string): number | null {
  const ham = String(form.get(ad) ?? "").trim().replace(",", ".");
  if (!ham) return null;
  const v = Number(ham);
  return Number.isFinite(v) ? v : NaN;
}

export async function POST(request: NextRequest) {
  const form = await request.formData();

  const toplam_sermaye = sayi(form, "toplam_sermaye");
  const deneme_sermaye = sayi(form, "deneme_sermaye");
  const temel_risk_pct = sayi(form, "temel_risk_pct");
  const max_tek_pozisyon_pct = sayi(form, "max_tek_pozisyon_pct");
  const max_tema_pct = sayi(form, "max_tema_pct");
  const enflasyon_yillik = sayi(form, "enflasyon_yillik");
  const mevduat_yillik = sayi(form, "mevduat_yillik");
  const sessiz_saat_baslangic = String(form.get("sessiz_saat_baslangic") ?? "").trim();
  const sessiz_saat_bitis = String(form.get("sessiz_saat_bitis") ?? "").trim();
  const gozlem_bolumu_aktif = form.get("gozlem_bolumu_aktif") === "1";

  const sayisalAlanlar = [
    toplam_sermaye, deneme_sermaye, temel_risk_pct,
    max_tek_pozisyon_pct, max_tema_pct, enflasyon_yillik, mevduat_yillik,
  ];
  if (sayisalAlanlar.some((v) => v !== null && Number.isNaN(v))) {
    return geri(request, "hata=sayi");
  }
  if ((toplam_sermaye ?? 0) < 0 || (deneme_sermaye ?? 0) < 0) {
    return geri(request, "hata=negatif");
  }
  const saatRegex = /^([01]\d|2[0-3]):([0-5]\d)$/;
  if (sessiz_saat_baslangic && !saatRegex.test(sessiz_saat_baslangic)) {
    return geri(request, "hata=saat");
  }
  if (sessiz_saat_bitis && !saatRegex.test(sessiz_saat_bitis)) {
    return geri(request, "hata=saat");
  }

  const client = db();
  const { error } = await client.from("user_settings").update({
    toplam_sermaye, deneme_sermaye, temel_risk_pct,
    max_tek_pozisyon_pct, max_tema_pct, enflasyon_yillik, mevduat_yillik,
    ...(sessiz_saat_baslangic ? { sessiz_saat_baslangic } : {}),
    ...(sessiz_saat_bitis ? { sessiz_saat_bitis } : {}),
    gozlem_bolumu_aktif,
    updated_at: new Date().toISOString(),
  }).eq("id", 1);
  if (error) return geri(request, "hata=kayit");

  return geri(request, "ok=kaydedildi");
}
