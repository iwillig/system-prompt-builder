# Research: designing system prompts for a Python coding agent

**Status:** research note
**Related:** [Prompt authoring](../prompts.rst), [Evaluation](../evaluation.rst), [fragment ablation research](fragment-ablation-evaluation.md), [fragments and composition](prompt-fragments-and-composition.md)

This note collects what first-party sources say about writing a system prompt
for a coding agent that works on Python, and what that implies for the
fragments SPB ships. Every claim cites the source that owns it. Where no primary
source supports a claim, it is marked **unverified** or left out.

## Conclusion

1. A system prompt should hold only what the model cannot discover and what must
   hold on every turn: role, evidence and verification rules, tool routing, and
   reporting rules. Python facts that live in the repository (layout, test
   command, formatter config) belong in project files, tools, or skills. [Claude Code best practices][cc-best] [Claude Code memory][cc-memory]
2. Python-specific text earns its place when it states a project decision or a
   command the model cannot infer. Generic style rules (PEP 8, docstring form)
   are probably already known to the model; restating them is plausible noise.
   No primary source measures the effect of Python-specific system prompt text.
   This is an evidence gap, not a finding. **Unverified.**
3. The strongest first-party guidance is about *verification*: give the agent a
   command that checks its work, ask for evidence of the run, and enforce
   non-negotiable checks outside the prompt. [Claude Code best practices][cc-best]
4. Length and contradiction are the main risks. Both Anthropic and OpenAI
   document degraded adherence from long or conflicting instructions. [Claude Code memory][cc-memory] [GPT-5 prompting guide][openai-gpt5]
5. Evaluate Python prompts by ablation on a suite with deterministic checks
   where possible. SWE-bench is the standard external benchmark, but it measures
   whole agent systems, not prompt fragments. [SWE-bench paper][swebench-paper] [SWE-bench site][swebench-site]

## 1. What belongs in a system prompt

### Placement by volatility and enforcement

| Content | Where it fits | Source |
| --- | --- | --- |
| Role, evidence rules, reporting rules | System prompt | [Anthropic best practices][claude-bp], [Gemini strategies][gemini-strategies] |
| Exact test, lint, typecheck commands; project quirks | Project file (`CLAUDE.md`, `AGENTS.md`) | [Claude Code best practices][cc-best], [AGENTS.md][agents-md] |
| Team procedures used occasionally (release, runbook) | Skill, loaded on demand | [Claude Code best practices][cc-best], [Agent Skills][agent-skills] |
| Rules with zero exceptions (formatter, protected paths, typecheck before finish) | Hook or deny rule, not prose | [Claude Code best practices][cc-best] |
| Per-repository facts the code already shows | Omit | [Claude Code best practices][cc-best] |

- Anthropic states the split directly: instructions in a prompt, `CLAUDE.md`, or
  a skill are non-deterministic ("there's no *guarantee* that it'll follow your
  instructions"), while a hook or deny rule is executed by the harness every
  time. [Claude Code best practices][cc-best]
- Claude Code gives a two-question test for project text: "Could it find this by
  reading the code?" and "Would it actually go and look?" If both are yes, leave
  it out. [Claude Code best practices][cc-best]
- Claude Code treats `CLAUDE.md` and auto memory as "context, not enforced
  configuration"; a rule that cannot have exceptions belongs in a hook.
  [Claude Code memory][cc-memory]
- AGENTS.md is a plain-Markdown "README for agents" with build and test commands
  among its common sections; the nearest file wins, and an explicit user prompt
  overrides all of them. [AGENTS.md][agents-md]
- OpenHands recommends a "succinct" repository file covering purpose, setup,
  structure, and the CI checks (linters, pre-commit hooks). [OpenHands repo skills][openhands-repo]
- Aider loads a small conventions file read-only, so it is cached when prompt
  caching is on. [Aider conventions][aider-conv]
- Anthropic describes skills as lighter on context than `CLAUDE.md`: the name and
  description are always visible, the body loads when the task calls for it.
  [Claude Code best practices][cc-best]

### Generic versus Python-specific

| Layer | Examples | Notes |
| --- | --- | --- |
| Generic (any language) | Role, read-before-claim, verify-before-report, minimal scope, honest reporting | Anthropic and OpenAI samples are language-neutral. [Anthropic best practices][claude-bp], [GPT-5 guide][openai-gpt5] |
| Language-specific | Interpreter and environment commands, type checker, test runner, import and packaging conventions | Most useful as commands and decisions, not tutorials. |
| Project-specific | Which of `ruff`/`mypy`/`pyright` is used, `just check`, `src/` layout | Belongs in project files or a template variable. |

SPB already separates these: `identity`, `output`, and `rules` are mostly generic
in shape, while `schema`, `facts`, `goals`, and `routing` are specific to the
Symbolic tool and its Python extractor. [SPB rules fragment][spb-rules] [SPB routing fragment][spb-routing] [SPB schema fragment][spb-schema]

### What first-party coding-agent prompts contain

- SWE-agent's default config uses a one-line system prompt ("You are a helpful
  assistant that can interact with a computer to solve tasks.") and puts the
  procedure in the instance template: reproduce the error with a script, fix,
  rerun the script, and think about edge cases. [SWE-agent default config][sweagent-config]
- The OpenAI Codex guide recommends starting from the standard prompt and adding
  "tactical" changes, preferring dedicated tools over shell commands, adding
  tests when behavior changes, and keeping builds and type checks passing.
  [Codex prompting guide][openai-codex]
- None of these first-party examples carry Python-specific tutorial text. The
  SWE-agent template names `python <filename.py>` only as the way to run a
  reproduction script. [SWE-agent default config][sweagent-config]

## 2. Python-specific instructions: signal versus noise

The table rates each topic by whether a primary source supports including it.
"Plausible" means the reasoning follows from a source but no measurement exists.

| Topic | Include? | Basis |
| --- | --- | --- |
| Environment and run commands (`python -m pytest`, `just check`) | Yes, as exact commands | Claude Code: the file "works best when it only holds what Claude couldn't work out" and the first listed item is the exact test, typecheck, and lint commands. [Claude Code best practices][cc-best] |
| Virtual environment | Only the project's chosen way to run tools | Python docs: activation is not required; you can call the environment's interpreter by full path. Environments are not movable or copyable. [venv docs][py-venv] |
| Test layout and discovery | Only deviations from convention | pytest discovers `test_*.py` and `*_test.py`, and recommends a `src` layout. A repo that follows this needs no prompt text. [pytest good practices][pytest-gp] |
| Typing | State the checker and strictness, not what annotations are | PEP 484: hints are not enforced at runtime and never mandatory; checkers are separate tools. mypy `--strict` and pyright `typeCheckingMode` are configuration facts. [PEP 484][pep484] [mypy CLI][mypy-cli] [pyright config][pyright-cfg] |
| Typed package marker | Only in packaging tasks | PEP 561: a package ships inline types with an empty `py.typed` file. [PEP 561][pep561] |
| Formatting and linting | Name the tool and command; enforce via hook if strict | Ruff is both linter and formatter and reads `pyproject.toml`. The model knows PEP 8; the project's tool config is the authority. [Ruff docs][ruff] [PEP 8][pep8] |
| PEP 8 rules (79 columns, import groups, naming) | Usually omit | PEP 8 says "A style guide is about consistency," so the project's formatter config outranks the generic number. A 79-column rule can contradict a Ruff line-length setting. [PEP 8][pep8] |
| Docstrings | Only if the project requires a convention | PEP 257 prescribes triple double quotes, a summary line, and imperative mood. Anthropic's minimal-scope sample says not to add docstrings to code you did not change. [PEP 257][pep257] [Anthropic best practices][claude-bp] |
| Error handling | Short, positive rule | PEP 8: name specific exceptions rather than a bare `except:`. Anthropic's sample limits validation to system boundaries. [PEP 8][pep8] [Anthropic best practices][claude-bp] |
| Imports | Omit unless project-specific | PEP 8 import grouping is tool-enforceable (Ruff fixes unused imports). [PEP 8][pep8] [Ruff docs][ruff] |
| Async | Unverified; no primary source on prompting for it | Include only if the repo mixes sync and async and the model errs. Test with an eval case first. |
| Packaging and metadata | Project-specific facts only | PEP 621: metadata lives in the `[project]` table of `pyproject.toml`; only `name` must be static. The model reading `pyproject.toml` learns more than a summary of the PEP. [PEP 621][pep621] |

### Why "noise" is a real cost

- Claude Code states that every line in `CLAUDE.md` "takes a little of Claude's
  attention on *every* task, whether it's relevant or not." [Claude Code best practices][cc-best]
- It also warns that if you keep adding emphasis to a line that is still missed,
  the file has grown too long or the line belongs in a hook. [Claude Code best practices][cc-best]
- Anthropic's overeagerness sample tells the model not to add docstrings,
  comments, or annotations to code it did not change. A Python fragment that
  says "always add type hints and docstrings" can conflict with that scope rule.
  [Anthropic best practices][claude-bp]

### Prompt text that targets known agent failure modes

These are generic, but they matter most for Python repositories with a test
suite:

- **Hard-coding to pass tests.** Anthropic provides a sample that asks for a
  general solution, forbids special-casing test inputs, and asks the agent to
  report incorrect or infeasible tests rather than work around them. [Anthropic best practices][claude-bp]
- **Speculating about unread code.** Anthropic's `investigate_before_answering`
  sample: "Never speculate about code you have not opened." [Anthropic best practices][claude-bp]
- **Over-eager exploration.** OpenAI's guide suggests early-stop criteria such as
  "Avoid over searching for context" and notes that Cursor softened
  "maximize_"-style wording after it caused excessive tool use. [GPT-5 prompting guide][openai-gpt5]

## 3. Grounding in evidence and verification

### Give the agent a check and ask for evidence

- Anthropic: "If it has nothing to run that tells it whether the work actually
  *is* done, 'looks done' is all it has to go on." Options are a test file, a
  linter, or a type checker. [Claude Code best practices][cc-best]
- Ask for evidence: "the command it ran and its output." "All tests pass" alone
  "tells you very little." [Claude Code best practices][cc-best]
- OpenAI's SWE-bench and Terminal-Bench instructions say to verify changes
  thoroughly and "routinely verify your code works." The Codex guide adds "add
  verify steps if you couldn't do something." [GPT-5 prompting guide][openai-gpt5] [Codex prompting guide][openai-codex]
- A reviewer asked to find problems "will always find *something*", so scope the
  review request (for example "skip style"). [Claude Code best practices][cc-best]

SPB's `rules` fragment already encodes this loop for Python: read source and
tests, make a focused edit, run focused tests, then `just check`, and "report
checks actually run and failures honestly." [SPB rules fragment][spb-rules]
The `output` fragment adds "Never claim tests passed unless they ran
successfully." [SPB output fragment][spb-output]

### Enforce what must not be skipped

- Put must-run checks in a `Stop` hook or CI, not only in prose. Anthropic notes
  that "Always typecheck before you finish" in `CLAUDE.md` "works most of the
  time, not every time." [Claude Code best practices][cc-best]
- Claude Code caps consecutive `Stop` hook blocks (eight with no tool call
  between them), so an enforced check cannot loop forever. [Claude Code best practices][cc-best]
- SPB has no hook layer; a system prompt can only request the check. State this
  limit in the fragment docs rather than implying enforcement.

### Uncertain and failed tool results

- Claude's tool API distinguishes an error result (`is_error: true`) from a
  normal result, and advises instructive error text that says what went wrong
  and what to try next. [Handle tool calls][claude-tool-errors]
- Tool results can carry untrusted content; Anthropic says to keep it inside
  `tool_result` blocks rather than in system prompts. [Handle tool calls][claude-tool-errors]
- Gemini's guide says an agent should not "assume it is not applicable without
  checking" and should avoid "premature conclusions." [Gemini prompting strategies][gemini-strategies]
- SPB's rules already separate outcomes: a parse error is not a zero-match
  result, an absent fact is not proof of absence, and no query result may be
  invented. [SPB rules fragment][spb-rules] [SPB schema fragment][spb-schema]

For Python checkers specifically, three outcome classes are worth naming in a
fragment: the tool did not run (missing, wrong environment), the tool ran and
reported findings, and the tool ran clean. Whether mypy's exit status is
documented was not confirmed: the mypy command-line page did not state it, so
do not hard-code exit-code claims for mypy. **Unverified.** [mypy CLI][mypy-cli]

## 4. Structure and length

### Ordering and sections

- Anthropic: a role in the system prompt "focuses Claude's behavior and tone,"
  and "even a single sentence makes a difference." [Anthropic best practices][claude-bp]
- Gemini: place "essential behavioral constraints, role definitions (persona),
  and output format requirements" in the system instruction or at the start.
  [Gemini prompting strategies][gemini-strategies]
- Anthropic: put long documents near the top and the query and instructions
  after them. This applies to long inputs, not to the system prompt's rules.
  [Anthropic best practices][claude-bp]

### XML and Markdown

- Anthropic: XML tags "help Claude parse complex prompts unambiguously" when a
  prompt mixes instructions, context, examples, and inputs; use consistent,
  descriptive tag names. [Anthropic best practices][claude-bp]
- Gemini: "Choose one format and use it consistently within a single prompt."
  [Gemini prompting strategies][gemini-strategies]
- Anthropic recommends `<example>` and `<examples>` tags so examples are not read
  as instructions, and 3 to 5 examples for best results. Gemini recommends
  examples but warns that too many may cause the model to over-fit them.
  [Anthropic best practices][claude-bp] [Gemini prompting strategies][gemini-strategies]
- SPB-specific escaping for XML values is covered in [xml-prompt-values.md](xml-prompt-values.md).

### Positive versus negative phrasing

- Anthropic: "Tell Claude what to do instead of what not to do" (for example,
  ask for flowing prose instead of "Do not use markdown"). [Anthropic best practices][claude-bp]
- Anthropic's own overeagerness and test-hardcoding samples still use negative
  rules ("Don't add features...", "Do not hard-code values"). Both forms appear
  in first-party guidance, so prefer positive phrasing and keep a negative rule
  where it names a specific failure. [Anthropic best practices][claude-bp]
- OpenAI warns against persuasive emphasis: Cursor found "maximize_" wording
  caused excessive tool use. Gemini says "Avoid unnecessary or overly persuasive
  language." [GPT-5 prompting guide][openai-gpt5] [Gemini prompting strategies][gemini-strategies]

### Contradictions

- OpenAI: "contradictory or vague instructions can be more damaging to GPT-5
  than to other models," because the model spends reasoning tokens reconciling
  them. [GPT-5 prompting guide][openai-gpt5]
- Claude Code: "if two instructions contradict each other, Claude may pick one
  arbitrarily." It offers `/doctor prompt-audit` to find conflicting or
  outdated instruction files. [Claude Code memory][cc-memory]
- Python-specific conflict candidates: a PEP 8 79-column rule versus the
  project's formatter width; "add docstrings everywhere" versus "no changes
  beyond what was asked"; "always use `mypy --strict`" versus a project that
  uses pyright. Use one source of truth per setting.
- SPB's `rules` text already carries an internal tension worth reviewing: rule 3
  says Symbolic `query` is "the default first tool, not grep or read", while the
  `routing` fragment says to read source for Python class methods, keyword
  calls, and docstrings. They are compatible if read as "query first, then read
  for what the extractor omits", but a model could read them as conflicting.
  [SPB rules fragment][spb-rules] [SPB routing fragment][spb-routing]

### Length versus performance

- Claude Code recommends under 200 lines per `CLAUDE.md`; "longer files consume
  more context and reduce adherence." [Claude Code memory][cc-memory]
- Claude Code's best-practices page says "the work is mostly removing lines"
  after `/init`. [Claude Code best practices][cc-best]
- No primary source gives a token threshold for a system prompt. The 200-line
  figure is a documented guideline for one product's project files, not a
  measured limit for system prompts. **Unverified as a general rule.**
- Codex guidance: start from a standard prompt and make tactical additions,
  rather than writing a large prompt from scratch. [Codex prompting guide][openai-codex]

## 5. Evaluating Python prompts

### External benchmarks

- **SWE-bench** (Jimenez et al., ICLR 2024): 2,294 problems from 12 popular
  Python repositories; the task is to edit the codebase to resolve a GitHub
  issue. At publication Claude 2 resolved 1.96%. [SWE-bench paper][swebench-paper] [SWE-bench site][swebench-site]
- **SWE-bench Verified** has 500 engineer-confirmed solvable problems; Lite is a
  smaller variant (the site gives no detail); Multimodal extends to visual
  domains. [SWE-bench site][swebench-site]
- **SWE-agent** (Yang et al.): argues the agent-computer interface (how an agent
  edits, navigates, and runs tests) affects performance. It reports 12.5% pass@1
  on SWE-bench at publication. This shows interface design matters; it does not
  isolate system prompt wording. [SWE-agent paper][sweagent-paper]
- SWE-bench is Python-only by repository selection, so it is a natural external
  check for a Python prompt. But it exercises a whole agent (tools, scaffold,
  model), and scoring needs a Docker-based harness. The site does not explain
  the pass criteria in the page we read. Do not read a SWE-bench delta as a
  fragment-level effect without ablating the scaffold constant. [SWE-bench site][swebench-site]
- OpenAI says its own SWE-bench and Terminal-Bench prompts emphasize thorough
  verification. This is evidence of what the vendor used, not a measured
  effect of that sentence. [GPT-5 prompting guide][openai-gpt5]

### Connecting to SPB's evaluation

SPB's current design already matches the cautions above:

- `spb eval ablate` drops or compresses one fragment against a shared baseline,
  default three repeats, and reports `REGRESSION`, `INDETERMINATE`, or
  `NO_REGRESSION_DETECTED`, scoped to the suite. [Evaluation docs](../evaluation.rst) [Ablation research](fragment-ablation-evaluation.md)
- Cases can assert exact ordered tool traces with `mock_tools` and
  `expected_tool_calls`. [Evaluation docs](../evaluation.rst)
- Compression applies only to fragments listed in `compressible_fragments`;
  identity and safety text stays byte-identical. [Prompt authoring](../prompts.rst)

Implications for Python fragments:

1. **Prefer deterministic assertions.** Cases such as "runs the project's check
   command before reporting" or "does not claim success after a failing tool
   result" can be asserted from the tool trace, not a judge score. This avoids
   the judge noise documented in the ablation note. [Ablation research](fragment-ablation-evaluation.md)
2. **Add negative-control cases.** Include a case where `pytest` fails and the
   expected answer reports the failure, and one where the tool errors rather
   than returning zero matches.
3. **Ablate per Python fragment.** Each proposed fragment below is a drop
   candidate; a fragment whose removal yields no regression across three
   repeats is a candidate for deletion, scoped to the suite.
4. **Keep suite scope honest.** Suite-scoped verdicts do not extend to SWE-bench
   or to other repositories.
5. **Track prompt size.** Report fragment token cost beside the verdict, since
   the documented risk of long prompts is lost adherence rather than hard
   failure. [Claude Code memory][cc-memory]

## 6. Recommendations for this project

### Proposed Python fragment set

Fragments are flat and selected by the system prompt; a fragment cannot include
another fragment. [Prompt authoring](../prompts.rst) The set below keeps generic
and Python-specific text apart so each can be ablated independently.

| Alias | Mode | Content | Basis |
| --- | --- | --- | --- |
| `identity` (exists) | template | One-sentence role, project, harness | Anthropic role guidance. [Anthropic best practices][claude-bp] |
| `python_env` (new) | template | Exact commands to run tests, lint, typecheck, and one test file, from variables | Claude Code: exact commands go in project text. [Claude Code best practices][cc-best] |
| `verification` (new; split from `rules` 5-6) | literal | Run the check, report command and output, label unverified claims, distinguish "did not run" / "findings" / "clean" | Anthropic evidence guidance; OpenAI verify steps. [Claude Code best practices][cc-best] [Codex prompting guide][openai-codex] |
| `scope` (new) | literal | Minimal-change rule: no unrequested refactors, docstrings, or annotations on untouched code; validate at boundaries | Anthropic overeagerness sample. [Anthropic best practices][claude-bp] |
| `general_solutions` (new) | literal | Do not special-case test inputs; report a wrong or infeasible test | Anthropic test-hardcoding sample. [Anthropic best practices][claude-bp] |
| `python_conventions` (new, optional) | template | Only project decisions: formatter and line length, checker and strictness, docstring convention if any, import style if non-default | PEP 8 consistency principle. [PEP 8][pep8] |
| `python_packaging` (new, optional) | literal | Edit `pyproject.toml` `[project]` metadata; add `py.typed` only for typed packages | PEP 621, PEP 561. [PEP 621][pep621] [PEP 561][pep561] |
| `routing`, `schema`, `facts`, `goals`, `tools`, `built_in_tools`, `output` (exist) | mixed | Symbolic-specific and reporting text | Existing fragments. |

Notes:

- `python_env` and `python_conventions` should take project values from template
  variables so they do not contradict `pyproject.toml`. Variables are declared
  in front matter. [Prompt authoring](../prompts.rst)
- Keep `python_conventions` empty for a project whose formatter already enforces
  style. The formatter is the authority; the fragment adds only what the tools
  cannot express. [Ruff docs][ruff] [PEP 8][pep8]
- Do not add PEP 8, PEP 257, or PEP 484 tutorial text. Cite them as the
  background for a rule, not as prompt content.
- Mark `verification`, `scope`, and `general_solutions` as not compressible
  (they are behavior-critical). `python_conventions` is a reasonable
  compression candidate. [Prompt authoring](../prompts.rst)
- Where a rule must always hold (formatter run, protected paths), document a
  harness hook in the project instead of strengthening the prompt wording.
  [Claude Code best practices][cc-best]

### Suggested eval cases to add

| Case | Assertion | Type |
| --- | --- | --- |
| Fix a bug in a small module | Trace reads source, edits, then runs the test command | Tool trace |
| Test fails after edit | Answer reports the failure and does not claim success | Judge plus phrase check |
| Checker command not found | Answer says the check did not run | Judge |
| Asked to make a failing test pass by special-casing | Answer implements the general fix or reports the test as wrong | Judge |
| Simple question | Short answer, no tool call | Tool trace (empty list) |
| Typo-level change | No added docstrings or annotations | Judge |

### Open questions

1. Does a Python-specific fragment move scores at all, or is the generic
   `verification` fragment responsible for most of the effect? The ablation tool
   can answer this on our suite; no primary source can.
2. Should `python_env` live in the system prompt, or in a project `AGENTS.md`
   that the harness injects? The first-party guidance favors project files for
   commands; SPB currently has no import path for them. [Claude Code best practices][cc-best] [AGENTS.md][agents-md]
3. Is a skill-style on-demand fragment (packaging, async) worth the loading
   model, given SPB appends skill text eagerly today? [Prompt fragments and composition](prompt-fragments-and-composition.md)
4. Which model families will run these prompts? Anthropic and OpenAI give
   model-specific advice (for example, Anthropic notes some models overengineer
   and OpenAI notes GPT-5 is sensitive to contradictions). Fragments may need a
   per-model ablation. [Anthropic best practices][claude-bp] [GPT-5 prompting guide][openai-gpt5]
5. Should the suite include a SWE-bench-style external check, given its harness
   cost and the scaffold confound? Not decided here.
6. Async, concurrency, and security-sensitive Python (subprocess, deserialization)
   have no first-party prompting guidance found. Treat any fragment on them as a
   hypothesis to test.

## Claims not traced to a primary source

- Any measured benefit of Python-specific system prompt text. No source found.
- A general token or line limit for system prompts; only product guidance for
  `CLAUDE.md` exists.
- mypy's exit status on errors (the page read did not state it).
- How SWE-bench computes pass/fail: the project site read here did not define it.
- Async-specific prompting benefits.

## Sources

Fetched 2026-10-28. Anthropic's `docs.claude.com` URLs redirect to
`platform.claude.com`; the page titled "System prompts" redirects to the
consolidated "Prompting best practices" page, so role and XML guidance below cite
that page.

[claude-bp]: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
[claude-tool-errors]: https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls
[cc-best]: https://code.claude.com/docs/en/best-practices
[cc-memory]: https://code.claude.com/docs/en/memory
[openai-gpt5]: https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide
[openai-codex]: https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide
[gemini-strategies]: https://ai.google.dev/gemini-api/docs/prompting-strategies
[gemini-sysinst]: https://ai.google.dev/gemini-api/docs/system-instructions
[agents-md]: https://agents.md/
[agent-skills]: https://agentskills.io/specification
[aider-conv]: https://aider.chat/docs/usage/conventions.html
[openhands-repo]: https://docs.openhands.dev/usage/prompting/microagents-repo
[sweagent-config]: https://raw.githubusercontent.com/SWE-agent/SWE-agent/main/config/default.yaml
[sweagent-paper]: https://arxiv.org/abs/2405.15793
[swebench-paper]: https://arxiv.org/abs/2310.06770
[swebench-site]: https://www.swebench.com/SWE-bench/
[pep8]: https://peps.python.org/pep-0008/
[pep257]: https://peps.python.org/pep-0257/
[pep484]: https://peps.python.org/pep-0484/
[pep561]: https://peps.python.org/pep-0561/
[pep621]: https://peps.python.org/pep-0621/
[pytest-gp]: https://docs.pytest.org/en/stable/explanation/goodpractices.html
[py-venv]: https://docs.python.org/3/library/venv.html
[ruff]: https://docs.astral.sh/ruff/
[mypy-cli]: https://mypy.readthedocs.io/en/stable/command_line.html
[pyright-cfg]: https://microsoft.github.io/pyright/#/configuration
[spb-rules]: ../../.spb/fragments/rules/FRAGMENT.md
[spb-routing]: ../../.spb/fragments/routing/FRAGMENT.md
[spb-schema]: ../../.spb/fragments/schema/FRAGMENT.md
[spb-output]: ../../.spb/fragments/output/FRAGMENT.md
