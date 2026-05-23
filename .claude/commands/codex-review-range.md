---
description: Codex code review against an explicit commit range (works around /codex:review's main…HEAD base-mismatch when work is committed directly to main)
argument-hint: [optional range like origin/main..HEAD or HEAD~3..HEAD; defaults to all unpushed commits]
---

You are running a Codex code review against an explicit commit range.

## Why this exists

The built-in `/codex:review` slash command uses `main…HEAD` as its diff base. In this project the user commits directly to `main`, so `main` and `HEAD` are usually the same commit and the diff is vacuously empty. The reviewer returns "no code changes" even when there's meaningful unreviewed work. This command sidesteps that by dispatching the `codex:codex-rescue` subagent with an explicit commit range.

## What to do

1. **Determine the range** to review:
   - If the user passed an argument (e.g., `HEAD~3..HEAD`, `c6def9c..b916a76`, `main~5..main`), use it verbatim.
   - Otherwise, default to `origin/main..HEAD` — every commit on the local branch that hasn't been pushed yet.
   - If `origin/main..HEAD` is empty (everything has been pushed), fall back to `HEAD~1..HEAD` (the most recent commit). If even that is empty, tell the user there's nothing to review.

2. **Show the range concretely** before launching. Run:
   ```bash
   cd "$(git rev-parse --show-toplevel)" && git log --oneline <range> && git diff --shortstat <range>
   ```
   Print the commit list + line-count so the user can confirm what's about to be reviewed.

3. **Estimate effort and pick foreground vs background**:
   - If the diff is roughly 1-2 files and small, foreground is fine.
   - Otherwise launch the rescue agent in the background.
   - Use `AskUserQuestion` once to confirm — but only if the size is genuinely ambiguous. For obvious cases, just launch.

4. **Dispatch the codex-rescue subagent** with a prompt structured like this:

   > Run a thorough Codex code review of the diff between commits `<BASE>` and `<HEAD_OR_TIP>` in the Asclepius repo at `/Users/nirav/Desktop/Claude Playground/Asclepius/`.
   >
   > The standard `/codex:review` slash command picked an empty base because of the main…HEAD mismatch; this run uses an explicit commit range to work around it.
   >
   > Concrete commands to start with:
   > ```
   > git diff <BASE>..<HEAD_OR_TIP> --stat
   > git log --oneline <BASE>..<HEAD_OR_TIP>
   > ```
   >
   > [Summary of what's in the range, derived from `git log` output. Include commit subjects and a short note of what each commit's intent is, drawn from the commit body. The goal is to give Codex enough context that the review can be specific.]
   >
   > Focus areas appropriate to the diff:
   > - Correctness: bugs, off-by-one, edge cases, race conditions
   > - Honesty: any place the code/docs/UI overclaim relative to what's implemented
   > - Architectural: does this slot cleanly into the registry / agent / methodology patterns, or does it create coupling?
   > - Tests: coverage gaps for the new code, especially failure modes
   > - Deploy: any new runtime dependencies, RAM concerns on Fly's 256MB shared-CPU-1x, or Vercel build implications
   >
   > Return a structured Codex-style review with severity-tagged findings (block / major / minor / nit) and an overall verdict (APPROVE / REQUEST CHANGES).

5. **Return Codex's output verbatim** when the rescue agent finishes. Same constraint as `/codex:review`: do not paraphrase, summarize, or add commentary inside Codex's section. After the verbatim output ends, it's fine to surface a brief follow-up paragraph naming the top 1-2 findings and asking how to proceed.

## Notes

- The `codex:codex-rescue` subagent is the same one `/codex:rescue` uses under the hood. It accepts freeform prompts and runs Codex against whatever the prompt asks.
- This command does NOT fix issues automatically — review-only, same as `/codex:review`.
- If the user wants per-finding remediation, they should ask explicitly after seeing the review.
- The structural alternative is to adopt a feature-branch workflow (work on `dev`, PR to `main`); this command is the workaround for solo-on-main contributors.
