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

// Analitik motor (faz 11) etiketleri — src/analytics.py ile senkron
export const KURULUM: Record<string, string> = {
  sikisma_kirilim_adayi: "sıkışma kırılım adayı",
  taban_kirilimi: "taban kırılımı (52h zirve)",
  momentum_devam: "momentum devamı",
  asiri_gerilme: "aşırı gerilme",
};

export const KATALIZOR: Record<string, string> = {
  birlesme_satinalma: "birleşme / satın alma",
  ihale_sozlesme: "ihale / sözleşme",
  regulasyon_onay: "regülasyon / onay",
  bilanco_surprizi: "bilanço sürprizi",
  arz_soku: "arz şoku",
  faiz_makro: "faiz / makro",
  genel: "genel",
};

export const REJIM: Record<string, { label: string; cls: string }> = {
  risk_on: { label: "risk iştahı açık", cls: "text-emerald-400" },
  notr: { label: "nötr", cls: "text-zinc-300" },
  risk_off: { label: "riskten kaçış", cls: "text-red-400" },
};

// Faz 12 kaynak çeşitlendirmesi — src/storage.py insert_thesis(kaynak=...) ile senkron
export const KAYNAK: Record<string, { label: string; cls: string }> = {
  haber: { label: "haber", cls: "bg-zinc-700 text-zinc-200" },
  teknik: { label: "📈 teknik", cls: "bg-sky-900 text-sky-200" },
  ikinci_derece: { label: "🔗 ikinci derece", cls: "bg-violet-900 text-violet-200" },
  geriye_donuk: { label: "geriye dönük", cls: "bg-zinc-700 text-zinc-300" },
};

export function tarih(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("tr-TR", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit", timeZone: "Europe/Istanbul",
  });
}

// İki ISO zaman damgası arasındaki tam gün farkı (karne: beklenen vs gerçekleşen ufuk)
export function gunSayisi(baslangicIso: string | null, bitisIso: string | null): number | null {
  if (!baslangicIso || !bitisIso) return null;
  const fark = new Date(bitisIso).getTime() - new Date(baslangicIso).getTime();
  return Math.round(fark / (1000 * 60 * 60 * 24));
}
