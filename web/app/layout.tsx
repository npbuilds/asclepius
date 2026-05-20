import type { Metadata } from "next";
import { Inter, Orbitron, Rajdhani, Share_Tech_Mono } from "next/font/google";
import Link from "next/link";

import { ThemeToggle } from "@/components/ThemeToggle";
import { ANTI_FOUC_SCRIPT } from "@/lib/theme";

import "./globals.css";

// Display / signage — Orbitron (geometric, uppercase feel)
const orbitron = Orbitron({
  subsets: ["latin"],
  weight: ["500", "600", "700", "800", "900"],
  variable: "--font-display",
  display: "swap",
});

// Data readouts — Share Tech Mono (monospace, terminal feel)
const shareTechMono = Share_Tech_Mono({
  subsets: ["latin"],
  weight: ["400"],
  variable: "--font-mono",
  display: "swap",
});

// UI body / chrome — Rajdhani (condensed humanist sans, cyberpunk reads as native)
const rajdhani = Rajdhani({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-body",
  display: "swap",
});

// Long-form prose — Inter (reading-optimized; the 20K-word methodology folder).
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-prose",
  display: "swap",
});

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
    <html
      lang="en"
      className={`${orbitron.variable} ${shareTechMono.variable} ${rajdhani.variable} ${inter.variable}`}
      suppressHydrationWarning
    >
      <head>
        {/* Anti-FOUC: set data-theme before paint based on localStorage */}
        <script dangerouslySetInnerHTML={{ __html: ANTI_FOUC_SCRIPT }} />
      </head>
      <body className="min-h-screen antialiased">
        <header className="border-b border-border-dim bg-bg-panel">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link
              href="/"
              className="font-display text-base font-bold uppercase tracking-[0.2em] text-cyan-bright"
            >
              Asclepius
            </Link>
            <nav className="flex items-center gap-6 text-xs uppercase tracking-wider text-text-dim">
              <Link
                href="/diligence/adagrasib"
                className="font-display hover:text-cyan-bright"
              >
                Worked example
              </Link>
              <Link
                href="/methodology"
                className="font-display hover:text-cyan-bright"
              >
                Methodology
              </Link>
              <a
                href="https://github.com/npbuilds/asclepius"
                target="_blank"
                rel="noreferrer"
                className="font-display hover:text-cyan-bright"
              >
                GitHub
              </a>
              <ThemeToggle />
            </nav>
          </div>
        </header>
        <main>{children}</main>
        <footer className="border-t border-border-dim bg-bg-panel">
          <div className="mx-auto max-w-6xl px-6 py-4 font-mono text-[11px] uppercase tracking-wider text-text-dim">
            Asclepius v0.1
          </div>
        </footer>
      </body>
    </html>
  );
}
