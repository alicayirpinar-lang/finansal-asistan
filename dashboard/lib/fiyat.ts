// Güncel fiyat: Yahoo chart API, sunucu tarafında ~5 dk önbellek (next revalidate).
// Alınamazsa null döner — sayfalar takip turu fiyatına / "fiyat yok"a düşer.

export type GuncelFiyat = {
  fiyat: number;
  onceki_kapanis: number | null;
  zaman: Date | null; // borsanın son işlem zamanı
};

function yahooTicker(symbol: string, market: string): string {
  return market === "BIST" ? `${symbol}.IS` : symbol;
}

export async function guncelFiyat(
  symbol: string,
  market: string,
): Promise<GuncelFiyat | null> {
  try {
    const t = yahooTicker(symbol, market);
    const res = await fetch(
      `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(t)}?range=1d&interval=5m`,
      {
        headers: { "User-Agent": "Mozilla/5.0 (compatible; finansal-asistan/1.0)" },
        next: { revalidate: 300 },
      },
    );
    if (!res.ok) return null;
    const j = await res.json();
    const meta = j?.chart?.result?.[0]?.meta;
    if (typeof meta?.regularMarketPrice !== "number") return null;
    return {
      fiyat: meta.regularMarketPrice,
      onceki_kapanis:
        typeof meta.chartPreviousClose === "number" ? meta.chartPreviousClose : null,
      zaman:
        typeof meta.regularMarketTime === "number"
          ? new Date(meta.regularMarketTime * 1000)
          : null,
    };
  } catch {
    return null;
  }
}

export async function guncelFiyatlar(
  list: { symbol: string; market: string }[],
): Promise<Record<string, GuncelFiyat>> {
  const uniq = new Map(list.map((x) => [`${x.symbol}|${x.market}`, x]));
  const out: Record<string, GuncelFiyat> = {};
  await Promise.all(
    [...uniq.values()].map(async (x) => {
      const f = await guncelFiyat(x.symbol, x.market);
      if (f) out[x.symbol] = f;
    }),
  );
  return out;
}
