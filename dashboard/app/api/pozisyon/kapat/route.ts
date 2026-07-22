// Pozisyon kapatma — tam veya kısmi. Adet boş/pozisyonun tamamıysa tam kapama:
// bağlı açık tez otomatik kullanici_satti olur (karneyi etkilemez). Adet
// pozisyondan azsa kısmi kapama: sadece miktar düşer, tez/durum değişmez
// (storage.close_position'daki Python mantığıyla aynı — plan bölüm 8).
import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/supabase";

function geri(request: NextRequest, param: string) {
  return NextResponse.redirect(new URL(`/portfoy?${param}`, request.url), 303);
}

export async function POST(request: NextRequest) {
  const form = await request.formData();
  const id = String(form.get("id") ?? "");
  const neden = String(form.get("neden") ?? "").trim().slice(0, 200);
  // Satış fiyatı: getiri metrikleri (XIRR/gerçekleşen K/Z) için gerekli;
  // boş bırakılırsa hesapta %0 varsayılır (metrics.py notlar'a yazar).
  const fiyatHam = String(form.get("fiyat") ?? "").trim().replace(",", ".");
  const fiyat = fiyatHam ? Number(fiyatHam) : null;
  const adetHam = String(form.get("adet") ?? "").trim().replace(",", ".");
  const adet = adetHam ? Number(adetHam) : null;
  if (!id) return geri(request, "hata=kapat");
  if (fiyat !== null && (!Number.isFinite(fiyat) || fiyat <= 0)) {
    return geri(request, "hata=kapatfiyat");
  }
  if (adet !== null && (!Number.isFinite(adet) || adet <= 0)) {
    return geri(request, "hata=kapatadet");
  }

  const client = db();
  const { data: pos } = await client.from("portfolio").select("*")
    .eq("id", id).eq("status", "acik").single();
  if (!pos) return geri(request, "hata=kapat");

  const tamKapama = adet === null || adet >= Number(pos.quantity);

  if (tamKapama) {
    const { error } = await client.from("portfolio").update({
      status: "kapali",
      closed_at: new Date().toISOString(),
      closed_quantity: pos.quantity,
      close_reason: neden || null,
      close_price: fiyat,
    }).eq("id", id);
    if (error) return geri(request, "hata=kapat");

    if (pos.thesis_id) {
      await client.from("theses").update({
        status: "kullanici_satti",
        resolved_at: new Date().toISOString(),
        resolution_note: neden || "kullanıcı dashboard'dan kapattı",
      }).eq("id", pos.thesis_id).eq("status", "acik");
    }
    return geri(request, "ok=kapatildi");
  }

  // Kısmi kapama: pozisyon açık kalır, sadece adet düşer.
  const { error } = await client.from("portfolio").update({
    quantity: Number(pos.quantity) - adet,
    closed_quantity: Number(pos.closed_quantity ?? 0) + adet,
    close_price: fiyat,
  }).eq("id", id);
  if (error) return geri(request, "hata=kapat");
  return geri(request, "ok=kismikapatildi");
}
