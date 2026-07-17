// Ortak Türkçe etiketler + renkler
export const DURUM: Record<string, { label: string; cls: string }> = {
  taslak: { label: "taslak", cls: "bg-zinc-700 text-zinc-200" },
  acik: { label: "açık", cls: "bg-blue-900 text-blue-200" },
  zayiflama_suphesi: { label: "zayıflama şüphesi", cls: "bg-amber-900 text-amber-200" },
  iptal_edildi: { label: "iptal", cls: "bg-zinc-800 text-zinc-400" },
  hedefe_ulasti: { label: "hedefe ulaştı 🎯", cls: "bg-emerald-900 text-emerald-200" },
  tez_bozuldu: { label: "tez bozuldu", cls: "bg-red-900 text-red-200" },
  suresi_doldu: { label: "süresi doldu", cls: "bg-zinc-700 text-zinc-300" },
  kullanici_satti: { label: "kullanıcı sattı", cls: "bg-purple-900 text-purple-200" },
};

export const GUVEN: Record<string, string> = {
  dusuk: "düşük", orta: "orta", yuksek: "yüksek",
};

export const YON: Record<string, string> = {
  yukselis: "↑ yükseliş", dusus: "↓ düşüş",
};

export function tarih(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("tr-TR", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit", timeZone: "Europe/Istanbul",
  });
}
