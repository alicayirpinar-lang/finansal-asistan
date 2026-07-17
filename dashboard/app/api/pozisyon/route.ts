// Pozisyon ekleme (dashboard formu). proxy.ts sayesinde giriş korumalı.
// Kurallar (plan bölüm 8): portfolio_type varsayılansız; tez seçilmediyse
// source=disaridan; kullanıcı isterse geriye dönük tez kuyruğa yazılır.
import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/supabase";

function geri(request: NextRequest, param: string) {
  return NextResponse.redirect(new URL(`/portfoy?${param}`, request.url), 303);
}

export async function POST(request: NextRequest) {
  const form = await request.formData();
  const symbol = String(form.get("sembol") ?? "").trim().toUpperCase();
  const market = String(form.get("pazar") ?? "");
  const quantity = Number(form.get("adet"));
  const entryPrice = Number(form.get("fiyat"));
  const entryDate = String(form.get("tarih") ?? "");
  const portfolioType = String(form.get("tur") ?? "");
  const thesisId = String(form.get("tez") ?? "").trim();
  const retroIstendi = form.get("retro") === "1";

  if (!/^[A-Z0-9.]{1,10}$/.test(symbol)) return geri(request, "hata=sembol");
  if (!["BIST", "US"].includes(market)) return geri(request, "hata=pazar");
  if (!Number.isFinite(quantity) || quantity <= 0) return geri(request, "hata=adet");
  if (!Number.isFinite(entryPrice) || entryPrice <= 0) return geri(request, "hata=fiyat");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(entryDate) ||
      entryDate > new Date().toISOString().slice(0, 10)) {
    return geri(request, "hata=tarih");
  }
  if (!["gercek", "deneme"].includes(portfolioType)) return geri(request, "hata=tur");

  const client = db();

  // FK için sembol satırı garanti edilir; config'ten gelen isim/temalar ezilmez.
  await client.from("symbols").upsert(
    { symbol, name: symbol, market },
    { onConflict: "symbol", ignoreDuplicates: true },
  );

  const { data: pos, error } = await client.from("portfolio").insert({
    symbol,
    market,
    quantity,
    entry_price: entryPrice,
    entry_date: entryDate,
    source: thesisId ? "sistem_tezi" : "disaridan",
    portfolio_type: portfolioType,
    thesis_id: thesisId || null,
  }).select("id").single();
  if (error || !pos) return geri(request, "hata=kayit");

  if (retroIstendi && !thesisId) {
    await client.from("retro_thesis_queue").insert({ position_id: pos.id, symbol });
    return geri(request, "ok=eklendi_retro");
  }
  return geri(request, "ok=eklendi");
}
