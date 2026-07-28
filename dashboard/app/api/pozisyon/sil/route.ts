// Yanlış girilen pozisyonu TAMAMEN siler (28 Temmuz 2026) — Kapat'ın aksine
// gerçek bir satış kaydı BIRAKMAZ ve bağlı tez varsa ona DOKUNMAZ (tez kendi
// gerçek kaderiyle — açık kalıp stop/hedef/süreyle kendi başına çözülür).
// RCL vakası: kapat kullanılınca gayet geçerli bir tez yanlışlıkla
// kullanici_satti oldu, sırf veri girişi hatası düzeltilmeye çalışılırken.
// Sadece açık pozisyon silinebilir — kapalı pozisyon kalıcı geçmiş kaydıdır.
import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/supabase";

function geri(request: NextRequest, param: string) {
  return NextResponse.redirect(new URL(`/portfoy?${param}`, request.url), 303);
}

export async function POST(request: NextRequest) {
  const form = await request.formData();
  const id = String(form.get("id") ?? "");
  if (!id) return geri(request, "hata=sil");

  const client = db();
  const { error } = await client.from("portfolio").delete()
    .eq("id", id).eq("status", "acik");
  if (error) return geri(request, "hata=sil");
  return geri(request, "ok=silindi");
}
