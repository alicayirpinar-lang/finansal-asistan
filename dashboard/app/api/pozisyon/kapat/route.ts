// Pozisyon kapatma (tam kapama). Bağlı açık tez otomatik kullanici_satti olur
// (storage.close_position ile aynı davranış; karneyi etkilemez).
// Kısmi kapama şimdilik bilgisayardaki manage.py'de.
import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/supabase";

function geri(request: NextRequest, param: string) {
  return NextResponse.redirect(new URL(`/portfoy?${param}`, request.url), 303);
}

export async function POST(request: NextRequest) {
  const form = await request.formData();
  const id = String(form.get("id") ?? "");
  const neden = String(form.get("neden") ?? "").trim().slice(0, 200);
  if (!id) return geri(request, "hata=kapat");

  const client = db();
  const { data: pos } = await client.from("portfolio").select("*")
    .eq("id", id).eq("status", "acik").single();
  if (!pos) return geri(request, "hata=kapat");

  const { error } = await client.from("portfolio").update({
    status: "kapali",
    closed_at: new Date().toISOString(),
    closed_quantity: pos.quantity,
    close_reason: neden || null,
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
