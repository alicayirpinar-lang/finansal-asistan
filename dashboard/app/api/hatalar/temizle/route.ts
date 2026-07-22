// Hata kaydını temizleme — sistem_hatalari sadece bir teşhis günlüğü, silinmesi
// hiçbir tez/pozisyon/karne verisini etkilemez. Onay istemi client tarafında.
import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/supabase";

export async function POST(request: NextRequest) {
  const { error } = await db().from("sistem_hatalari")
    .delete().gte("created_at", "1970-01-01");
  return NextResponse.redirect(
    new URL(`/hatalar?${error ? "hata=temizle" : "ok=temizlendi"}`, request.url),
    303,
  );
}
