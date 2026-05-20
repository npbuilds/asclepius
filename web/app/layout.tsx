import type { Metadata } from "next";
import Link from "next/link";

import "./globals.css";

export const metadata: Metadata = {
  title: "Asclepius — Biotech Venture Valuation",
  description:
    "Phase-gated PoS with a reflexivity adjustment, rNPV with Monte Carlo, 8-pillar diligence scorecard, and cited deal comparables.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <header className="border-b border-ink-200 bg-white">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link href="/" className="font-serif text-xl text-ink-900">
              Asclepius
            </Link>
            <nav className="flex gap-6 text-sm">
              <Link href="/diligence/adagrasib" className="hover:text-accent-600">
                Worked example
              </Link>
              <Link href="/methodology" className="hover:text-accent-600">
                Methodology
              </Link>
              <a
                href="https://github.com"
                target="_blank"
                rel="noreferrer"
                className="hover:text-accent-600"
              >
                GitHub
              </a>
            </nav>
          </div>
        </header>
        <main>{children}</main>
        <footer className="border-t border-ink-200 bg-white">
          <div className="mx-auto max-w-6xl px-6 py-6 text-xs text-ink-400">
            Asclepius v0.1 — methodology and base rates cited from BIO/Informa,
            Wong 2019, and Damodaran 2025. Adagrasib backtest framed as
            retrospective calibration, not prediction.
          </div>
        </footer>
      </body>
    </html>
  );
}
