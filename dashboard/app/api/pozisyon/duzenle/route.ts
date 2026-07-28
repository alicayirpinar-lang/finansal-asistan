// Açık pozisyon düzenleme (28 Temmuz 2026): yanlış fiyat/adet/tarih girildiğinde
// kapat/aç döngüsüne gerek kalmasın diye eklendi — Kapat her zaman gerçek bir
// satış sayıp bağlı tezi kullanici_satti yapıyordu, bu da veri-girişi hatalarını
// düzeltmeye çalışırken gerçek tezleri kirletiyordu (RCL vakası). Sadece açık
// pozisyon düzenlenebilir; kapalı pozisyon kalıcı geçmiş kaydıdır.
import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/supabase";

function geri(request: NextRequest, param: string) {
  return NextResponse.redirect(new URL(`/portfoy?${param}`, request.url), 303);
}

export async function POST(request: NextRequest) {
  const form = await request.formData();
  const id = String(form.get("id") ?? "");
  const quantity = Number(form.get("adet"));
  const entryPrice = Number(form.get("fiyat"));
  const entryDate = String(form.get("tarih") ?? "");

  if (!id) return geri(request, "hata=duzenle");
  if (!Number.isFinite(quantity) || quantity <= 0) return geri(request, "hata=duzenleadet");
  if (!Number.isFinite(entryPrice) || entryPrice <= 0) return geri(request, "hata=duzenlefiyat");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(entryDate) ||
      entryDate > new Date().toISOString().slice(0, 10)) {
    return geri(request, "hata=duzenletarih");
  }

  const client = db();
  const { error } = await client.from("portfolio").update({
    quantity, entry_price: entryPrice, entry_date: entryDate,
  }).eq("id", id).eq("status", "acik");
  if (error) return geri(request, "hata=duzenle");
  return geri(request, "ok=duzenlendi");
}
