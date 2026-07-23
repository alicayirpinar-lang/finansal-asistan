// Periyodik tarama tetikleyici (23 Temmuz 2026 bulgusu) — GitHub Actions'ın
// kendi `schedule:` cron'u sık (15 dk) tetiklemelerde güvenilir çalışmıyor
// (gözlem: 6s45dk'da 27 yerine 3 koşu). cron-job.org bunu güvenilir şekilde
// yapıyor — kritik-tarama'daki KANITLI aynı desen (bkz. o dosyanın GitHub
// tetikleme bloğu), burada haber/RSS/Telegram mantığı olmadan, koşulsuz.
const REPO = "alicayirpinar-lang/finansal-asistan";

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status, headers: { "Content-Type": "application/json" },
  });
}

Deno.serve(async (req) => {
  const url = new URL(req.url);
  if (url.searchParams.get("key") !== Deno.env.get("CRON_SECRET_PERIYODIK")) {
    return json({ error: "unauthorized" }, 401);
  }

  const pat = Deno.env.get("GH_PAT");
  if (!pat) return json({ error: "GH_PAT tanımlı değil" }, 500);

  const res = await fetch(
    `https://api.github.com/repos/${REPO}/actions/workflows/tarama.yml/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${pat}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ref: "main", inputs: { kaynak: "periyodik" } }),
    },
  );

  return json({ triggered: res.status === 204, status: res.status });
});
