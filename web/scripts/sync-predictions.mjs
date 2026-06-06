// Sync predictions/*.json from the repo root into a TS module the web app imports.
//
// Same pattern as sync-methodology.mjs — see that file's header for the
// Vercel-only-deploys-web/-subdir constraint that motivates this approach.
// In short: predictions live in the repo root; Vercel only sees web/;
// so we generate web/lib/predictions-content.ts from the source JSONs
// pre-build and commit the generated file. Local dev re-syncs on every
// typecheck / build.

import { existsSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, "..", "..");
const PREDICTIONS_DIR = join(REPO_ROOT, "predictions");
const OUTPUT_PATH = join(__dirname, "..", "lib", "predictions-content.ts");

if (!existsSync(PREDICTIONS_DIR)) {
  if (existsSync(OUTPUT_PATH)) {
    console.log(
      "sync-predictions: source directory not found (expected outside the " +
        "monorepo), using committed predictions-content.ts as-is",
    );
  } else {
    console.warn(
      "sync-predictions: WARNING — source directory not found AND committed " +
        "predictions-content.ts is missing; predictions page will be empty",
    );
    writeFileSync(OUTPUT_PATH, "export const PUBLIC_PREDICTIONS = [];\n");
  }
  process.exit(0);
}

const entries = readdirSync(PREDICTIONS_DIR).filter((f) => f.endsWith(".json"));
const predictions = [];

for (const filename of entries.sort()) {
  const raw = readFileSync(join(PREDICTIONS_DIR, filename), "utf8");
  try {
    const data = JSON.parse(raw);
    predictions.push({ filename, ...data });
  } catch (err) {
    console.warn(`sync-predictions: skipping ${filename} — ${err.message}`);
  }
}

// Sort by prediction_date descending (newest first). Resolution-pending
// predictions float to the top — they're the open commitments. Resolved
// ones below — they're the track record.
predictions.sort((a, b) => {
  // Pending (no resolution.outcome) first
  const aResolved = a.resolution?.outcome != null;
  const bResolved = b.resolution?.outcome != null;
  if (aResolved !== bResolved) return aResolved ? 1 : -1;
  // Then by prediction_date descending
  return (b.prediction_date || "").localeCompare(a.prediction_date || "");
});

const fileHeader = `// AUTO-GENERATED from predictions/*.json by web/scripts/sync-predictions.mjs.
// Do not edit by hand. Run \`pnpm sync:predictions\` (or any typecheck/build)
// to regenerate. The JSON shape mirrors the schema documented in
// methodology/10-public-prediction-log.md.

`;

const body = `export const PUBLIC_PREDICTIONS = ${JSON.stringify(predictions, null, 2)} as const;\n`;

writeFileSync(OUTPUT_PATH, fileHeader + body);
console.log(
  `synced ${predictions.length} predictions → lib/predictions-content.ts`,
);
