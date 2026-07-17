// Next 16: middleware.ts yerine proxy.ts — tüm sayfalar giriş korumalı.
import { NextRequest, NextResponse } from "next/server";
import { COOKIE_NAME, verifyToken } from "@/lib/auth";

export default function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (pathname.startsWith("/giris") || pathname.startsWith("/api/giris")) {
    return NextResponse.next();
  }
  const token = request.cookies.get(COOKIE_NAME)?.value;
  if (!verifyToken(token)) {
    return NextResponse.redirect(new URL("/giris", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
