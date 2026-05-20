import type { Config } from "tailwindcss";
import typography from "@tailwindcss/typography";

// Helper: build a Tailwind color object backed by a CSS-variable RGB triplet.
// Lets utility classes work with opacity modifiers (e.g. `bg-cyan-bright/30`).
const fromVar = (name: string) => `rgb(var(--${name}-rgb) / <alpha-value>)`;

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Surfaces
        "bg-deep": fromVar("bg-deep"),
        "bg-panel": fromVar("bg-panel"),
        "bg-panel-hover": fromVar("bg-panel-hover"),
        "border-dim": fromVar("border-dim"),
        "border-glow": fromVar("border-glow"),

        // Accents (faded + bright variants per spec)
        "cyan-faded": fromVar("cyan-faded"),
        "cyan-bright": fromVar("cyan-bright"),
        "magenta-faded": fromVar("magenta-faded"),
        "magenta-bright": fromVar("magenta-bright"),
        "amber-faded": fromVar("amber-faded"),
        "amber-bright": fromVar("amber-bright"),

        // Semantic
        "red-faded": fromVar("red-faded"),
        "red-bright": fromVar("red-bright"),
        "green-faded": fromVar("green-faded"),
        "green-bright": fromVar("green-bright"),

        // Text
        "text-primary": fromVar("text-primary"),
        "text-dim": fromVar("text-dim"),
        "text-bright": fromVar("text-bright"),
      },
      borderRadius: {
        // Sharp corners per spec — override Tailwind defaults
        DEFAULT: "var(--radius)",
        sm: "calc(var(--radius) - 2px)",
        md: "var(--radius)",
        lg: "calc(var(--radius) + 2px)",
        xl: "calc(var(--radius) + 4px)",
      },
      fontFamily: {
        // CSS-variable-driven for Next.js next/font integration.
        // Fallbacks ensure pages render readably even if a font fails to load.
        display: ["var(--font-display)", "Orbitron", "sans-serif"],
        mono: [
          "var(--font-mono)",
          "Share Tech Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "monospace",
        ],
        body: ["var(--font-body)", "Rajdhani", "ui-sans-serif", "system-ui", "sans-serif"],
        prose: [
          "var(--font-prose)",
          "Inter Variable",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        // Default `font-sans` falls back to body (Rajdhani) so any unconverted
        // class doesn't regress to the OS default.
        sans: ["var(--font-body)", "Rajdhani", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [typography],
};

export default config;
