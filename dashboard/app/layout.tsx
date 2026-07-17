import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Finansal Asistan",
  description: "Kişisel fırsat radarı paneli",
};

const NAV = [
  { href: "/", label: "Özet" },
  { href: "/tezler", label: "Tezler" },
  { href: "/portfoy", label: "Portföy" },
  { href: "/getiri", label: "Getiri" },
  { href: "/gozlem", label: "Gözlem" },
  { href: "/karne", label: "Karne" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <body className="min-h-screen bg-zinc-950 text-zinc-100 antialiased">
        <nav className="border-b border-zinc-800 bg-zinc-900/80 sticky top-0 backdrop-blur z-10">
          <div className="mx-auto max-w-5xl px-4 py-3 flex items-center gap-5 overflow-x-auto">
            <span className="font-semibold text-emerald-400 whitespace-nowrap">📡 Finansal Asistan</span>
            {NAV.map((n) => (
              <Link key={n.href} href={n.href}
                className="text-sm text-zinc-300 hover:text-white whitespace-nowrap">
                {n.label}
              </Link>
            ))}
          </div>
        </nav>
        <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
        <footer className="mx-auto max-w-5xl px-4 py-8 text-xs text-zinc-500">
          Bu panel kişisel analiz aracıdır; yatırım tavsiyesi değildir.
        </footer>
      </body>
    </html>
  );
}
