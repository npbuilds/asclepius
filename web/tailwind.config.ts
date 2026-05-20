import type { Config } from "tailwindcss";
import typography from "@tailwindcss/typography";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Asclepius palette: deep navy + parchment + a single accent for the
        // reflexivity slider's "you're moving an important number" signal.
        ink: {
          50: "#f7f8fb",
          100: "#eef0f6",
          200: "#d6dbe7",
          400: "#7d869f",
          600: "#3f4a66",
          800: "#1c2238",
          900: "#0c1024",
        },
        accent: {
          50: "#fef3ec",
          400: "#f0a050",
          600: "#c47416",
          700: "#9a5807",
        },
        good: { 500: "#3a9a64" },
        bad: { 500: "#c4503b" },
      },
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "-apple-system",
          "BlinkMacSystemFont",
          "Inter",
          "Segoe UI",
          "system-ui",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
        serif: ["ui-serif", "Iowan Old Style", "Georgia", "serif"],
      },
    },
  },
  plugins: [typography],
};

export default config;
