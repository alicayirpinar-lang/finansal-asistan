// Kritik hızlı yol (plan bölüm 11) — 7/24 nöbetçi.
// cron-job.org 5 dakikada bir çağırır. Dar kritik kelime setiyle birkaç RSS'i tarar;
// yeni kritik haber görürse: (1) Telegram'a anlık haber, (2) GitHub tarama
// workflow'unu workflow_dispatch ile tetikler (tam analiz Python tarafında —
// beyin burada KOPYALANMAZ, tek beyin ilkesi).
import { createClient } from "npm:@supabase/supabase-js@2";

// Not: Google News, bazı bulut IP'lerini engelleyebiliyor — bu yüzden liste
// sunucu-dostu doğrudan RSS kaynakları ağırlıklı (BBC/CNBC/AA/BloombergHT).
const FEEDS = [
  "https://feeds.bbci.co.uk/news/world/rss.xml",
  "https://www.cnbc.com/id/100727362/device/rss/rss.html",
  "https://www.aa.com.tr/tr/rss/default?cat=ekonomi",
  "https://www.bloomberght.com/rss",
  "https://news.google.com/rss/search?q=war+declared+OR+embargo+markets&hl=en-US&gl=US&ceid=US:en",
];

// config.py CRITICAL_KEYWORDS ile senkron tutulmalı (dar set, bilinçli)
const CRITICAL = [
  "savaş ilan", "declares war", "war declared",
  "ambargo", "embargo",
  "boğaz kapat", "strait clos", "hürmüz kapat", "hormuz clos",
  "olağanüstü faiz", "emergency rate",
  "askeri operasyon başla", "military operation launch",
  "nükleer", "nuclear strike",
  "sıkıyönetim", "martial law",
  "temerrüt", "default on debt",
];

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status, headers: { "Content-Type": "application/json" },
  });
}

function normalize(title: string) {
  return title.toLowerCase().replace(/[^a-z0-9ğüşıöçâî ]/g, "").slice(0, 120);
}

async function fetchTitles(url: string): Promise<{ titles: string[]; diag: string }> {
  try {
    const res = await fetch(url, {
      signal: AbortSignal.timeout(8000),
      headers: { "User-Agent": "Mozilla/5.0 (compatible; finansal-asistan/1.0)" },
    });
    const xml = await res.text();
    const matches = xml.matchAll(
      /<item>[\s\S]*?<title>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?<\/title>/g,
    );
    const titles = [...matches].map((m) => m[1].trim()).slice(0, 25);
    return { titles, diag: `${res.status}/${xml.length}b/${titles.length}` };
  } catch (e) {
    return { titles: [], diag: `err:${String(e).slice(0, 60)}` }; // nöbet durmaz
  }
}

Deno.serve(async (req) => {
  // Basit koruma: cron-job.org URL'sindeki gizli anahtar eşleşmeli
  const url = new URL(req.url);
  if (url.searchParams.get("key") !== Deno.env.get("CRON_SECRET")) {
    return json({ error: "unauthorized" }, 401);
  }

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  );

  // Tüm kaynakları paralel tara
  const results = await Promise.all(FEEDS.map(fetchTitles));
  const allTitles = results.flatMap((r) => r.titles);
  const diag = results.map((r) => r.diag);
  const hits = allTitles.filter((t) => {
    const low = t.toLowerCase();
    return CRITICAL.some((k) => low.includes(k));
  });

  // 7 günden eski dedup kayıtlarını temizle (tablo şişmesin)
  await supabase.from("critical_seen").delete()
    .lt("created_at", new Date(Date.now() - 7 * 86400e3).toISOString());

  if (!hits.length) return json({ checked: allTitles.length, fresh: 0, diag });

  // Dedup: daha önce görülen başlık tekrar tetiklemez
  const fresh: string[] = [];
  for (const title of hits.slice(0, 5)) {
    const norm = normalize(title);
    const { data } = await supabase.from("critical_seen")
      .select("id").eq("title_norm", norm).limit(1);
    if (!data?.length) {
      await supabase.from("critical_seen").insert({ title_norm: norm, title });
      fresh.push(title);
    }
  }
  if (!fresh.length) return json({ checked: allTitles.length, fresh: 0 });

  // 1) Anlık Telegram haberi (7/24, sessiz saat yok — kritik seviye)
  const tgToken = Deno.env.get("TG_TOKEN");
  const tgChat = Deno.env.get("TG_CHAT");
  if (tgToken && tgChat) {
    await fetch(`https://api.telegram.org/bot${tgToken}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: tgChat,
        text: `🚨 KRİTİK HABER YAKALANDI (7/24 radar)\n${fresh.map((t) => "• " + t).join("\n")}\n\nTam analiz başlatıldı — tez bildirimi birkaç dakika içinde gelebilir.`,
        disable_web_page_preview: true,
      }),
    });
  }

  // 2) GitHub tarama workflow'unu anında tetikle (tam analiz Python'da)
  let triggered = false;
  const pat = Deno.env.get("GH_PAT");
  if (pat) {
    const res = await fetch(
      "https://api.github.com/repos/alicayirpinar-lang/finansal-asistan/actions/workflows/tarama.yml/dispatches",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${pat}`,
          Accept: "application/vnd.github+json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ ref: "main" }),
      },
    );
    triggered = res.status === 204;
  }

  return json({ checked: allTitles.length, fresh: fresh.length, triggered });
});
