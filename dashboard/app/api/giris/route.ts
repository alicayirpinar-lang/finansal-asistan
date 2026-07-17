import { NextRequest, NextResponse } from "next/server";
import { COOKIE_NAME, signToken } from "@/lib/auth";

export async function POST(request: NextRequest) {
  const form = await request.formData();
  const sifre = form.get("sifre");
  if (!process.env.SITE_PASSWORD || sifre !== process.env.SITE_PASSWORD) {
    return NextResponse.redirect(new URL("/giris?hata=1", request.url), 303);
  }
  const response = NextResponse.redirect(new URL("/", request.url), 303);
  response.cookies.set(COOKIE_NAME, signToken(), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 90, // 90 gün
    path: "/",
  });
  return response;
}
