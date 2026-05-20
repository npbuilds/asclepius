"use client";

import { useEffect, useMemo, useState } from "react";
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";

import { runScorecard } from "@/lib/api-client";
import type { ModulePanelProps } from "@/lib/module-registry";
import type { Recommendation, ScorecardInput } from "@/lib/types";

const PILLAR_NAMES = [
  "clinical",
  "regulatory",
  "competitive",
  "manufacturing",
  "ip",
  "financial",
  "team",
  "computational",
] as const;
type PillarName = (typeof PILLAR_NAMES)[number];

const DEFAULT_INPUT: ScorecardInput = {
  clinical: { score: 7 },
  regulatory: { score: 7 },
  competitive: { score: 6 },
  manufacturing: { score: 7 },
  ip: { score: 7 },
  financial: { score: 6 },
  team: { score: 7 },
  computational: { score: 5 },
  red_flags: [],
  green_flags: [],
};

const REC_COLOR: Record<Recommendation, string> = {
  strong_buy: "bg-green-bright text-white",
  buy: "bg-green-bright/20 text-green-bright",
  hold: "bg-bg-panel-hover text-text-primary",
  cautious: "bg-cyan-bright/10 text-cyan-bright",
  avoid: "bg-red-bright/20 text-red-bright",
};

export default function ScorecardRadarPanel({ record, setRecord }: ModulePanelProps) {
  const [input, setInput] = useState<ScorecardInput>(DEFAULT_INPUT);

  useEffect(() => {
    let cancelled = false;
    runScorecard(record.asset, input)
      .then((scorecard) => !cancelled && setRecord({ scorecard }))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(input), JSON.stringify(record.asset)]);

  const scorecard = record.scorecard;

  const radarData = useMemo(() => {
    return PILLAR_NAMES.map((name) => ({
      pillar: name,
      score: input[name].score,
    }));
  }, [input]);

  return (
    <section className="rounded border border-border-dim bg-bg-panel p-5">
      <h2 className="mb-4 font-display text-lg text-text-bright">
        8-Pillar Scorecard
      </h2>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_auto]">
        <div className="space-y-2">
          {PILLAR_NAMES.map((name) => (
            <PillarSlider
              key={name}
              name={name}
              value={input[name].score}
              onChange={(v) =>
                setInput({ ...input, [name]: { score: v } })
              }
            />
          ))}

          <FlagInput
            label="Red flags (auto-cap recommendation)"
            placeholder="e.g. going concern, CRL"
            flags={input.red_flags}
            onChange={(red_flags) => setInput({ ...input, red_flags })}
            accent="bad"
          />
          <FlagInput
            label="Green flags (+0.5 each)"
            placeholder="e.g. Big Pharma partnership"
            flags={input.green_flags}
            onChange={(green_flags) => setInput({ ...input, green_flags })}
            accent="good"
          />
        </div>

        <div className="lg:w-64">
          <ResponsiveContainer width="100%" height={220}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="var(--border-dim)" />
              <PolarAngleAxis dataKey="pillar" tick={{ fontSize: 10 }} />
              <PolarRadiusAxis domain={[0, 10]} tick={false} axisLine={false} />
              <Radar
                dataKey="score"
                stroke="var(--cyan-bright)"
                fill="var(--cyan-bright)"
                fillOpacity={0.3}
              />
            </RadarChart>
          </ResponsiveContainer>

          {scorecard ? (
            <div className="mt-3 text-sm">
              <div className="text-[10px] uppercase tracking-wide text-text-dim">
                Aggregate
              </div>
              <div className="text-2xl font-medium tabular-nums text-text-bright">
                {scorecard.aggregate_score.toFixed(2)} / 10
              </div>
              <div
                className={`mt-2 inline-block rounded px-2 py-0.5 text-xs uppercase tracking-wide ${REC_COLOR[scorecard.recommendation]}`}
              >
                {scorecard.recommendation.replace("_", " ")}
              </div>
              {scorecard.red_flags.length ? (
                <div className="mt-2 text-[11px] text-red-bright">
                  {scorecard.red_flags.length} red flag
                  {scorecard.red_flags.length > 1 ? "s" : ""} — recommendation capped
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function PillarSlider({
  name,
  value,
  onChange,
}: {
  name: PillarName;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="grid grid-cols-[100px_1fr_30px] items-center gap-2 text-xs">
      <span className="capitalize text-text-primary">{name}</span>
      <input
        type="range"
        min={1}
        max={10}
        step={0.5}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-cyan-bright"
      />
      <span className="text-right font-mono tabular-nums text-text-bright">
        {value.toFixed(1)}
      </span>
    </label>
  );
}

function FlagInput({
  label,
  placeholder,
  flags,
  onChange,
  accent,
}: {
  label: string;
  placeholder: string;
  flags: string[];
  onChange: (flags: string[]) => void;
  accent: "good" | "bad";
}) {
  const [draft, setDraft] = useState("");
  function add() {
    const v = draft.trim();
    if (!v) return;
    onChange([...flags, v]);
    setDraft("");
  }
  return (
    <div className="mt-3 text-xs">
      <div className="mb-1 uppercase tracking-wide text-text-dim">{label}</div>
      <div className="flex gap-2">
        <input
          value={draft}
          placeholder={placeholder}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && add()}
          className="flex-1 rounded border border-border-dim px-2 py-1"
        />
        <button
          type="button"
          onClick={add}
          className="rounded border border-cyan-bright bg-cyan-bright/10 px-2 py-1 font-display text-[11px] uppercase tracking-wider text-cyan-bright hover:bg-cyan-bright/20"
        >
          Add
        </button>
      </div>
      {flags.length ? (
        <ul className="mt-2 flex flex-wrap gap-1">
          {flags.map((f, i) => (
            <li
              key={i}
              className={`rounded-full border px-2 py-0.5 ${
                accent === "bad"
                  ? "border-red-bright/30 bg-red-bright/10 text-red-bright"
                  : "border-green-bright/30 bg-green-bright/10 text-green-bright"
              }`}
            >
              {f}
              <button
                onClick={() => onChange(flags.filter((_, j) => j !== i))}
                className="ml-1 hover:opacity-70"
                aria-label="Remove"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
