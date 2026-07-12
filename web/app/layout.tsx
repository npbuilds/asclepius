import type { Metadata } from "next";
import { Inter, Orbitron, Rajdhani, Share_Tech_Mono } from "next/font/google";
import Link from "next/link";

import { PersonaToggle } from "@/components/PersonaToggle";
import { SendFeedback } from "@/components/SendFeedback";
import { ThemeToggle } from "@/components/ThemeToggle";
import { METHODOLOGY_COUNT } from "@/lib/methodology-count";
import { PERSONA_ANTI_FOUC_SCRIPT } from "@/lib/persona";
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

// metadataBase resolves relative URLs (including the auto-generated
// opengraph-image.tsx) against the canonical production URL so social
// crawlers (LinkedIn, Twitter, Slack) get absolute links. Next.js falls
// back to localhost otherwise, which produces broken previews. The
// opengraph-image / twitter-image route conventions auto-populate the
// images: [] arrays so we don't have to list them here.
export const metadata: Metadata = {
  metadataBase: new URL("https://asclepius-bio.vercel.app"),
  title: "Asclepius — Biotech Venture Valuation",
  description:
    "Phase-gated PoS with reflexivity + supply-constraint path-dependencies, rNPV with Monte Carlo, a defensible investment memo, and cited deal comparables.",
  openGraph: {
    title: "Asclepius — Biotech Venture Valuation",
    description:
      `Reflexivity- and supply-adjusted PoS · phase-gated rNPV · a defensible memo · ${METHODOLOGY_COUNT} cited methodology writeups.`,
    url: "https://asclepius-bio.vercel.app",
    siteName: "Asclepius",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Asclepius — Biotech Venture Valuation",
    description:
      "Reflexivity-adjusted PoS · phase-gated rNPV · ML prior externally validated against CT Open.",
  },
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
        {/* Anti-FOUC: set data-theme + data-persona before paint based on
            localStorage. Both scripts are tiny synchronous reads + DOM
            attribute writes; running them inline in <head> eliminates the
            flash-of-wrong-theme / flash-of-wrong-persona on deep links. */}
        <script dangerouslySetInnerHTML={{ __html: ANTI_FOUC_SCRIPT }} />
        <script dangerouslySetInnerHTML={{ __html: PERSONA_ANTI_FOUC_SCRIPT }} />
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
                href="/portfolio"
                className="font-display hover:text-cyan-bright"
              >
                Portfolio
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
              <SendFeedback />
              <PersonaToggle />
              <ThemeToggle />
            </nav>
          </div>
        </header>
        <main>{children}</main>
        <footer className="border-t border-border-dim bg-bg-panel">
          <div className="mx-auto flex max-w-6xl items-center gap-3 px-6 py-3 font-mono text-[11px] uppercase tracking-wider text-text-dim">
            <span>── Asclepius ──</span>
            <span className="text-cyan-bright">●</span>
            <span>v0.1</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
