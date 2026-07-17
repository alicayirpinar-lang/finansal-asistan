// Tek şifreli giriş + HMAC imzalı cookie (daha-once sitesindeki desenin aynısı).
import { createHmac, timingSafeEqual } from "crypto";

const COOKIE_NAME = "fa_oturum";
const PAYLOAD = "finansal-asistan-v1";

function secret() {
  return process.env.SITE_PASSWORD || "";
}

export function signToken(): string {
  return createHmac("sha256", secret()).update(PAYLOAD).digest("hex");
}

export function verifyToken(token: string | undefined): boolean {
  if (!token || !secret()) return false;
  const expected = signToken();
  try {
    return timingSafeEqual(Buffer.from(token), Buffer.from(expected));
  } catch {
    return false;
  }
}

export { COOKIE_NAME };
