# Plan: fragment ablation reliability

**Status:** implemented and verified offline.
**Related:** [Fragment ablation and compression-sweep evaluation](fragment-ablation-evaluation.md)
**Goal:** preserve completed work after an interrupted ablation, reject ambiguous
suite identities before model calls, and record enough compression provenance
to interpret rate-sweep results.

## Scope and constraints

Keep the existing ablation verdict rules, case-generation cap, and shared baseline.
Do not add automatic retries, resume, a new compression engine, or a CI failure
gate. A partial report is evidence from completed runs; it is not a complete
comparison and must not claim a verdict for an unfinished variant. Never record
credentials or the full environment in provenance.

## 1. Checkpoint completed runs

- [x] Resolve the final output path before evaluation starts. Use a separate,
   clearly named partial path next to it, such as `<output>.partial`. Do not
   overwrite an existing final report when a new run fails. Show the partial
   path in the CLI when a checkpoint exists.
- [x] Add a checkpoint callback or writer to `evaluate_fragment_plan`. Invoke it
   after every successfully completed and validated baseline or variant repeat,
   and after a completed variant has been aggregated. Keep the callback
   optional so callers can still use the API without writing files.
- [x] Give the partial artifact an explicit schema version and `status: incomplete`.
   Include the plan, suite and prompt hashes, harness, repeat count, completed
   baseline runs, and each variant's identity, provenance, completed runs, and
   progress. Include an outcome only after all repeats for that variant and the
   baseline have passed validation and aggregation. Record the last completed
   phase and current variant/repeat, without treating an interrupted run as a
   completed observation. Do not serialize exception messages that may contain
   credentials or response bodies.
- [x] Serialize each `EvaluationRun` once when it is checkpointed. Its current
   `as_dict()` creates a timestamp on each call; repeated checkpoint writes must
   not make an earlier run appear to have happened later.
- [x] Write checkpoints atomically: write a temporary file in the destination
   directory, flush and close it, then replace the partial file. If a checkpoint
   write fails, stop the run and report the error; do not silently spend more
   endpoint calls without preservation. Keep the last valid checkpoint when
   possible. Do not mask the original evaluation error if cleanup also fails.
- [x] After all variants finish, write the existing complete report atomically to
   the final path, mark it complete, and remove the partial file only after the
   final write succeeds. If the final write fails, retain the partial report.
   Preserve existing complete-report fields and verdicts; document added fields.
- [x] On an endpoint error or `KeyboardInterrupt`, retain the latest checkpoint,
   return a nonzero exit status, and identify the partial path. Do not promise
   recovery from a process kill, machine failure, or failure during the first
   repeat. A repeat is the checkpoint unit: an interrupted `run_evaluation`
   may have completed cases, but those cases are not returned and are not saved.
   Resume and case-level checkpoints are out of scope.

## 2. Validate identities before calls

- [x] Validate case names and effective metric names (`spec.name or spec.type`) for
   uniqueness before planning, compression, or evaluation. Use the same helper
   for suites loaded from YAML and suites passed directly to the ablation API.
   Report the duplicate identity and whether it is a case or metric.
- [x] Apply the check in `load_evaluation_suite` so other suite consumers also fail
   early. Call the helper at the ablation API boundary as well, since callers
   can construct `EvaluationSuite` directly. Document this validation change.
- [x] Keep the duplicate and mismatch guards in aggregation as defense against
   malformed or inconsistent run results. Do not rely on case count alone.
- [x] Check that both normal CLI execution and `--dry-run` reject duplicates before
   the compressor or evaluation runner is called. Names are exact,
   case-sensitive identities, matching current aggregation behavior.

## 3. Preserve compression provenance

- [x] Extend each planned rate variant to retain the `CompressionResult`
   compressor and settings instead of discarding them. Record the alias, target
   rate, and input and output fragment SHA-256 hashes. Keep the composed prompt
   hash and character reduction already present in the report.
- [x] Make `compress_prompt` report the actual LLMLingua model and device used,
   along with its rate and relevant fixed options. Resolve configuration in one
   place shared by compressor creation and provenance. Account for the cached
   compressor: changing environment variables after the first load must not
   cause the report to name a configuration different from the loaded instance.
   Do not load LLMLingua just to report settings for `compressor=none`.
- [x] Store this information in each rate outcome and partial variant record. A
   drop variant should explicitly have no compressor provenance. `none` must be
   recorded as `none`, even when its output equals the baseline. Retain existing
   transformation labels and report fields for compatibility.
- [x] Describe the fields and their limits in `docs/evaluation.rst`. Hashes and
   model identifiers support auditing but do not guarantee identical output
   across dependency versions, model revisions, or hardware. Record available
   compressor package version and model revision if they can be obtained
   reliably; otherwise document that they are not captured rather than guessing.

## Tests and verification

- [x] Add offline tests in `tests/test_fragment_eval.py` for failures during the
   baseline, during a later variant, and during final report writing. Assert
   that completed runs survive, incomplete variants have no verdict, a prior
   final report is preserved on failure, and success replaces the final report
   and removes the partial file. Test `KeyboardInterrupt`, checkpoint write
   failure, stable serialized timestamps, and atomic replacement behavior.
- [x] Add suite-loader and ablation tests for duplicate case names, duplicate
   explicit metric names, and collisions between explicit names and default
   metric types. Assert that neither compression nor evaluation is called in
   live and dry-run preflight. Test a directly constructed suite too.
- [x] Stub the compressor to verify exact settings and fragment hashes in planned,
   partial, and final artifacts. Cover `none`, LLMLingua configuration overrides,
   cache behavior, and drops. Do not require a model download or endpoint.
- [x] Run `pipenv run pytest tests/test_fragment_eval.py tests/test_evaluation.py`
   and the relevant compression tests. Run `just check` for the full quality
   gates and `just docs` for the documentation changes. Record any unavailable
   checks or failures. A live endpoint run is optional and must use an explicit
   cost cap; offline tests do not establish live endpoint reliability.

## Acceptance criteria

- [x] A failure after a completed repeat leaves a readable, explicitly incomplete
  checkpoint containing every completed repeat and no invented verdicts.
- [x] A completed run produces a compatible final report, and an unsuccessful run
  does not replace an earlier final report.
- [x] Ambiguous suite identities fail before compression or model calls, including
  in dry runs and direct ablation API use.
- [x] Rate reports identify the actual compressor and available settings used for
  each variant; drop reports do not imply compression.
- [x] Existing verdict behavior remains unchanged, and the checks above pass.

## Verification record

- Focused ablation, suite, and compression tests passed.
- `just check` passed, including the full pytest suite.
- `just docs` passed. No live endpoint run was performed.
