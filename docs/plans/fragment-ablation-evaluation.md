# Plan: fragment ablation and compression-sweep evaluation

**Status:** first release implemented and verified with a bounded live endpoint run. Full-suite sweep not yet verified; combined-candidate search and CI gating remain proposed.
**Research:** [`../research/fragment-ablation-evaluation.md`](../research/fragment-ablation-evaluation.md)
**Goal:** measure how dropping or compressing one selected fragment affects
this evaluation suite, without claiming that undetected harm proves redundancy.

## Scope

Add an `spb eval ablate` command that reports what happens when one selected
fragment is dropped or one compressible fragment is compressed at a specified
rate. It produces a fragment-by-case-and-metric matrix. Every variant holds the
other fragments, layout, and suite fixed. This measures only the tested suite,
not whether a fragment is universally unnecessary.

Reuse `render_prompt`, `compose_fragment_content`, `compress_prompt`, and
`run_evaluation`; no new judge or compression engine. An uncompressed baseline
is shared across all variants in one report. The current `run_evaluation` returns
scores and exact tool-call comparisons for each case. Proposed conclusions are
`REGRESSION`, `NO_REGRESSION_DETECTED`, and `INDETERMINATE`. The middle label
means precisely that the configured suite did not detect harm in this run. It
does not certify that removal or compression is safe in other contexts.

True isolation (a fragment alone), greedy minimal-prompt search, and new metric
types are out of scope. Greedy search must not treat `NO_REGRESSION_DETECTED` as
proof that multiple fragments can be removed together: interactions require
re-evaluating each combined candidate.

## Core concepts

- **Baseline:** the full uncompressed prompt, run `repeats` times and reused in
  every comparison within one report. Do not reuse results across changed suite,
  prompt, model, harness, or evaluation settings.
- **Variant:** one `(alias, drop)` or `(alias, rate)` transformation. Mutate a copy
  of `rendered_fragments` and recompose; preserve all other prompt inputs.
- **Observation:** a case-and-metric score/pass pair or a case's exact expected
  tool-trace pass/fail. Preserve every run as well as aggregate counts and scores.
- **Verdict:** a scoped inference about a variant against the tested baseline,
  with explicit reasons and an `exploratory` marker when `repeats < 3`.

## Aggregation and verdict contract

Run at least three repeats by default. For each `(case, metric name)`, collect
scores, threshold, passed count, median, minimum, and maximum separately for
baseline and variant. Reject mismatched or duplicate case/metric identities,
thresholds, or run counts rather than silently comparing unlike observations.
Determine aggregate pass by strict majority of the recorded `passed` values;
with an even-numbered tie, mark it mixed, not passed. Keep median and minimum
as diagnostics, not competing pass/fail definitions. Compare the same case and
metric on both sides; aggregate mean is descriptive, not the verdict rule.

For expected tool calls, record pass counts per case across repeats. Exact
trace equality is a deterministic check of *one output*, but model-generated
traces can vary. Treat an all-pass baseline as stable; a baseline with any trace
failure is unstable for that case. On a stable baseline, a strict-majority
variant trace failure is a regression signal. If variant passes and failures
are mixed but failures do not form a strict majority, it is indeterminate.
Report trace counts and actual traces even when the baseline is unstable. Do
not claim a single failure proves the model will always fail. An unstable baseline cannot support a tool-trace regression claim.

Apply this ordered decision table:

1. **REGRESSION:** on a baseline case/metric that passed every repeat, the
   variant has a strict-majority failure; or a stable baseline tool expectation
   has a strict-majority variant failure. This is an observed repeat-level
   regression signal, even in an exploratory run.
2. **INDETERMINATE:** no regression signal, but fewer than three repeats,
   any baseline metric does not pass every repeat, a baseline tool expectation
   is unstable, variant results are mixed or tied, or a baseline-passing metric
   shows a material score decrease without a pass/fail flip. A material
   decrease means baseline median minus variant median exceeds `noise_floor`.
   A baseline that never passes a metric cannot establish preservation of that
   metric; record it as uncovered, not as evidence of safety.
3. **NO_REGRESSION_DETECTED:** at least three repeats, no regression signal or
   indeterminate condition, and every baseline metric/tool expectation
   passed every baseline repeat and every variant repeat. Scope this label to
   the suite, model, repeat count, and compared prompt hashes. Do not call it
   `REDUNDANT` or `safe to compress`.

`noise_floor` (default 0.10) is only a diagnostic guard for a material median
score decrease with no threshold flip; it cannot convert uncertain evidence
into safety. A future near-threshold diagnostic must not change metric pass/fail semantics.
Report the minimum score as a worst-case observation, not an automatic
regression trigger. Any
uncovered baseline metric makes the variant `INDETERMINATE` unless a regression
signal elsewhere takes precedence. List uncovered metrics prominently.

For rate sweeps, report each rate independently; compression outputs are not
assumed monotone. The smallest rate (fraction of tokens kept) with
`NO_REGRESSION_DETECTED` is an *observed* best rate on this grid, not a
certified maximum-safe compression rate.

## Data model

The implementation in `src/spb/fragment_eval.py` uses `FragmentVariant` and
`FragmentPlan` for immutable variant inputs and preflight counts, and
`FragmentAblationReport` for provenance and YAML output. Aggregation returns
case-and-metric rows with raw scores, pass counts, threshold, median, minimum,
and maximum. Tool-call rows retain per-run traces and pass counts. Each outcome
records a verdict, reasons, exploratory status, content hash, and character
reduction. The matrix has one row per `(alias, transformation, case, metric)`;
baseline and variant runs retain their full result payloads.

Preserve enough raw evidence to audit every aggregated decision. The artifact
should label character reduction as a proxy for cost, not token savings.

## Core functions

The module builds a variant by copying `rendered_fragments`, replacing
exactly one selected alias, and calling `compose_fragment_content`. Validate
both alias existence and compressibility for a rate variant. Do not modify the
original prompt or its source fragment provenance; record the variant values,
transformation, and composed content digest separately. Reject a compression
result that is empty, as the existing fragment compression path does.

One orchestration function takes drop aliases and rate variants together,
builds the complete plan first, checks the preflight cap, runs the baseline
`repeats` times, then runs each variant `repeats` times. It aggregates matched
case/metric and trace observations, applies the verdict table, and writes a
report. Pure aggregation helpers and the variant builder are independently
testable offline. Do not expose separate top-level sweep runners that would
accidentally run the baseline twice in `--mode both`.

`write_fragment_report` writes the report as YAML with both the matrix and raw
per-run evidence. Existing evaluation writer behavior is a reference for file
handling, not a reason to discard provenance.

## CLI

`spb eval ablate PROMPT` accepts `--suite`, `--harness`, `--var`,
`--mode drop|rate|both`, `--fragments`, `--rates`, `--compressor`,
`--repeats` (default 3), `--noise-floor` (default 0.10), `--dry-run`,
`--output`, `--project-root`, and optional `--max-case-generations`.
`case_tolerance` is deferred: it cannot change metric pass/fail semantics.

`--dry-run` renders and validates all variants without calling a model. Print
each variant's content hash and character reduction plus the planned count:
`(1 + number_of_variants) * repeats * number_of_cases`. This counts **case
generations**, not all endpoint requests: each case can make multiple judge or
tool-loop calls, and malformed-JSON judge retries add calls. Do not present it
as a hard token, monetary, or total-request estimate. For live runs, show the
same plan before invoking the model. If `--max-case-generations` is set and the
planned count exceeds it, fail *before* the first model call. This preflight
cap does not prevent mid-run judge retries from adding endpoint requests.

Validate `repeats >= 1`, unique fragment aliases, distinct rates in `(0, 1]`,
compressible-alias eligibility for rate sweeps, and non-empty composed
variants. Record validation and unexpected endpoint errors separately from
verdicts. Do not treat every regression found during an exploratory ablation
as a CLI failure: a separate opt-in gate can fail on `REGRESSION` once the
verdict contract is tested. No `--max-score-drop` is needed for a categorical
regression gate; mean score is diagnostic.

## Reporting: the matrix

Print a compact table with fragment, transformation, median-mean change,
character reduction, affected `(case, metric)` pairs, trace pass counts,
verdict, and reasons. Write a YAML artifact with raw per-repeat runs and a
matrix keyed by variant and `(case, metric)`; tool traces have their own
per-case rows. Flag uncovered baseline metrics and exploratory runs visibly.

Show each rate as a separate row. The lowest rate with
`NO_REGRESSION_DETECTED` is an observed grid result, not a guarantee that
still-lower rates or combinations of compressed fragments work.

## Milestones and verification

- **M0: offline verdict and aggregation.** Test keyed metric aggregation,
  thresholds and pass-count majority, even ties, unstable or uncovered
  baselines, tool traces, material score decrease, repeated runs, and the
  ordered verdict table. No endpoint calls.
- **M1: offline variant construction.** Test one-alias mutations, layout and
  skill preservation, allowed compression, non-empty variants, and hashes.
- **M2: orchestration and report.** Fake `run_evaluation`; verify baseline
  reuse across drop and rate variants, exact planned generation counts,
  artifact evidence, and matrix identity keys.
- **M3: CLI and dry run.** Offline tests verify dry run performs no evaluation
  calls, the opt-in generation cap fails before evaluation, and live planning
  prints the same count. Live endpoint smoke remains a separate verification
  step before relying on a sweep's verdict.
- **M4 (optional):** combined-candidate search or true isolation requires
  re-evaluating interactions and a separate design decision.

Do not run a full rate sweep against the live endpoint before offline tests
and dry-run cost estimation pass.

## Grounding notes

The existing composition seam is `compose_fragment_content` in
`src/spb/rendering.py`; it recomposes selected aliases with the same layout and
appended skills. `compress_prompt` in `src/spb/compression.py` accepts a rate
meaning fraction of tokens retained. `run_evaluation` in
`src/spb/evaluation.py` records metric name, threshold, pass result, reason,
and exact expected-tool-call comparison per case. These are syntax and source
observations, not a guarantee of stable model behavior. Raw result and
provenance fields should be retained in the new report.

## Follow-on decisions

1. Whether a future CI gate should fail on `REGRESSION` only, or also on
   `INDETERMINATE`. The first release can report without gating.
2. Whether a later version should enforce a *real* total endpoint-request or
   token budget by instrumenting the model/judge calls. The first-release cap
   only bounds planned case generations.
3. Whether to keep `case_tolerance`; it is optional for the first release and
   must not change metric pass/fail semantics.
