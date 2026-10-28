# Research: fragment ablation and compression-sweep evaluation

**Status:** research note
**Companion plan:** [`../plans/fragment-ablation-evaluation.md`](../plans/fragment-ablation-evaluation.md)

This note records the prior art and findings that shape the fragment-evaluation
feature: a tool that, for a composed prompt, evaluates variants where one
fragment is dropped or compressed at various rates, and reports whether outcomes
survive.

## The question, in the literature's terms

What we want to answer — *"can I remove or shrink fragment X and still get the
same outcomes?"* — is the same tradeoff the prompt-compression literature
studies, but at **component granularity** and for **system prompts** rather than
retrieval context.

### Compression fidelity is measured with stable metrics, not judge deltas

- **LLMLingua** (Qiu et al., EMNLP 2023, arXiv:2310.05736): coarse-to-fine
  compression with a *budget controller*; reports "up to 20× compression with
  little performance loss" measured by **downstream task accuracy** on GSM8K/BBH
  and perplexity, not by an LLM re-reading the prompt.
- **Selective Context** (Xia et al., 2023, arXiv:2310.06201): 50% context
  reduction → "only a minor drop of **.023 in BERTscore** and **.038 in
  faithfulness**." The headline numbers are deltas in *reference-guided* metrics.
- **LongLLMLingua** (Jiang et al., ACL 2024, arXiv:2403.12968): formulates
  compression as a **token-classification problem "to guarantee the faithfulness
  of the compressed prompt to the original one"** — i.e. the explicit goal is
  outcome preservation, which is exactly our premise.
- **RECOMP** (Xu et al., ICLR 2024, arXiv:2310.04408): compresses retrieved
  context and **can return the empty string** when the document adds no
  information — a built-in notion of *redundant* component, the same verdict our
  ablation wants to produce.

**Implication.** The field's unit of "same outcomes" is a stable, reference-
guided or task-accuracy metric. Our suite's metric is a reference-free
LLM-judge (G-Eval). That gap is the central design constraint: judge deltas are
noisier than the BERTscore/accuracy deltas these papers report, so the feature
must not treat a raw judge-score delta as a verdict on its own.

### The judge we use is a G-Eval-style reference-free evaluator — and those are noisy

- **G-Eval** (Liu et al., EMNLP 2023, arXiv:2303.16634): CoT + form-filling LLM
  metric. Reports **Spearman correlation ≈ 0.514 with human** judgment on
  summarization. A 0.5 correlation means a large fraction of the per-run score
  is judge noise, not signal.
- **Judging LLM-based Judges / MT-Bench** (Zheng et al., NeurIPS 2023,
  arXiv:2306.05685): documents **position bias, verbosity bias, self-enhancement
  bias**, and limited reasoning. Verbosity bias is directly relevant: it is the
  exact failure our own eval judge keeps penalizing ("irrelevant verbosity").

**Implication.** With a ~0.5-human-correlation reference-free judge, a
fragment's "effect" under ~0.1–0.15 of mean score is indistinguishable from
noise on a single run (we observed the identical prompt score 0.725 and 0.883
across runs, and one case flip 0.6 → 0.9). The verdict must therefore be
**threshold-based and repeat-aggregated**, not a raw-delta comparison.

## Closest existing tooling, and the gap

- **promptfoo** (promptfoo.dev, docs "Expected outputs / assertions"):
  config-driven eval. You declare multiple full **prompts** and a set of
  **tests**, and it runs the grid with **deterministic assertions** plus
  **model-graded** assertions. It answers "prompt A vs prompt B." It does **not**
  do intra-prompt *component ablation* (drop section X of one composed prompt
  while holding the rest constant) and has no *compression-rate sweep* concept.
- **DSPy / OPRO / APE**: treat instructions as optimizable modules. These
  *optimize* prompts; none *attribute* outcomes to individual fragments or
  reports a per-fragment importance matrix.

**Gap / positioning.** There is no dominant tool that takes a *composed*
(fragment + layout) prompt and produces a **fragment × eval-case responsibility
matrix** plus a **compression-rate curve** per fragment. That is the niche this
feature occupies: systematic component ablation and compression sweep for
composed system prompts, with judge-variance handling.

## Design consequences (carried into the plan)

1. **Conclusions are suite-scoped.** `NO_REGRESSION_DETECTED` does not imply a
   fragment is redundant or compression is universally safe.
2. **Repeat before a non-regression verdict.** Require at least three runs;
   aggregate by case and metric, preserve each run, and report unstable or
   uncovered baseline cases as indeterminate.
3. **Treat tool calls as stochastic observations.** Comparing a trace with
   expected calls is exact for one generated response; it does not make the
   model's next response deterministic. Compare pass counts with a stable
   baseline, and retain the raw traces.
4. **Use thresholds and a score-decrease guard.** A stable baseline becoming a
   majority failure signals regression; a material score drop without a
   threshold flip remains indeterminate. The noise floor cannot prove safety.
5. **Show cost honestly.** Rate is the fraction of tokens kept, but report
   output character reduction as a proxy, not a token count. Preflight count
   case generations across baseline and variants; judge retries and tool loops
   mean this is not an endpoint-request ceiling.
