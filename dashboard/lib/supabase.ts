// Sunucu tarafı Supabase istemcisi — SERVICE key sadece sunucuda kalır,
// tarayıcıya asla gitmez (tüm sayfalar server component).
import { createClient } from "@supabase/supabase-js";

export function db() {
  return createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_KEY!, {
    auth: { persistSession: false },
  });
}
