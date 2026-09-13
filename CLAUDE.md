# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific
instructions as needed.

Tradeoff: These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

Minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

Touch only what you must. Clean up only your own mess.

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

Define success criteria. Loop until verified.

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require
constant clarification.

---

## 5. Project: Mayen

### Where things are written down

Three places, and each fact belongs to exactly one of them. This file was 869 lines because
it carried a third copy of everything; it was compacted on 2026-08-15.

| | holds | read it when |
|---|---|---|
| `docs/ARCHITECTURE.md` (Turkish) | the design and every decision behind it. **Source of truth.** | before proposing anything structural |
| `docs/PLAN.md` | work packages P1–P28: what each did, why, and what it rejected | you need the history of a choice |
| `docs/README.md` | the index of the other 57 files, and **which of them are readings and which are generator output** | before opening or quoting any `docs/faz*` file |
| module docstrings (20% of `src/`) | why *this* code is shaped this way | you are editing that file |
| **this file** | only what a new session must know before touching the code | always — it is loaded every session |

If you find yourself writing a package narrative here, it belongs in `docs/PLAN.md`. If you
find yourself writing a rationale for one module, it belongs in that module's docstring.

### What it is

A voice assistant. Turkish speech in, English speech out. Single machine, local models
only, owns its own data. Single owner, plus other people who may speak to it with limited
privileges.

First-release capabilities: weather, date/time, contacts, notes, course schedule, system
metrics, Wake-on-LAN, reminders/scheduled tasks. **Faz 8 added a memory-write tool and
machine control** — volume, media, window actions, launching allow-listed applications
(§9.3). Twenty-two tools, catalog 1069 tokens.

Out of scope: multi-user accounts, remote/internet access, cloud models.

`ARCHITECTURE.md`'s meta-rule (§19): **items marked AÇIK (open) are not implemented until
answered. Assumptions are never substituted for them.** If a task depends on an open item,
say which one and stop — don't pick a default.

### Current state

**Phases 1–6 are closed. P1–P28 are all done.**
`docs/PLAN.md` has all of them. **`./baslat` is the whole running system except the LLM**:
it starts the Kokoro TTS service, the app, and a Qt window wired to the speaker, and takes
`--stt fake|real --tts fake|real` (defaults fake/real). It deliberately does *not* start
`llama-server` — that one is swapped by hand during measurement, so it stays manual and
`baslat` only warns when its port is dead. Parts still run alone: `uv run --env-file .env
python -m mayen` plus `python -m client` (text), `--ses` (voice), `--gui` (+`--ses` for
audio).

**The permanent way to run it is systemd user units, installed 2026-08-17; `baslat` is now
the dev script, not the answer to "how do I run this".** `config/` holds three:
`mayen.service` and `mayen-kokoro.service` (both enabled, `Wants=`/`After=` between them —
**never `Requires=`**, a dead TTS makes the assistant silent, not broken), and
`mayen-llm@.service`, a template started by model name
(`systemctl --user start mayen-llm@Qwen3.8-27B-IQ4_XS`) and **deliberately never enabled**,
because the hand-swap decision stands. They are symlinked into `~/.config/systemd/user/`,
so editing the file in `config/` *is* editing the unit. SearXNG is not a unit — docker's own
`restart: unless-stopped` owns it; two lifetimes for one process is the thing being avoided.
`baslat` needs no change and gets more correct here: it treats a listening port as ready, so
with the units up it only opens the window.

**`mayen-llm@.service` decides production's sampling**, because `main.py:454` reads it off
`/props` (`server_sampling()`, the owner's call — a model tuned to its own temperature can
arrive). Today the unit carries `--temp 0.7 --top-p 0.8 --top-k 20 --presence-penalty 1.5`,
while **every number in `docs/` was read greedy**. That gap has never been measured;
`evals --ornekleme sunucu` is the instrument, and it has never been run.

**Faz 7's three items are all done (2026-08-16): role text personality → English output →
Kokoro TTS** (`docs/faz7-rol.md`, `docs/faz7-kokoro.md`). `config/rol.txt` is now Ixion's **Edden** (the
Tiqqun's Personal Assistant: flat, terse, calls the owner "Administrator") and §2's "output
English" decision is finally *implemented* — it never was before. The cost taken knowingly:
`bellek` 94 → 82, `halusinasyon` and the golden set unharmed, and **it was adopted on 27B
without the 35B check** by the owner's call. §19.15 (Turkish proper nouns through an
English voice) stays open on purpose — the owner chose to measure it after Kokoro is wired,
which it now is, so **it is measurable and still unmeasured**.

**TTS is real: Kokoro, in its own process** (`services/kokoro/`, own uv project, own
`.venv` — torch never enters the repo's). §19.2's TTS half is closed. The adapter
(`adapters/kokoro.py`) is a thin HTTP client; the model, the ffmpeg effect chain and the
24→16 kHz conversion all live service-side. Three things worth knowing before touching it:
**it runs on CPU and that is a measured constraint** (`llama-server` holds 15.6 of the
card's 16 GB; Kokoro couldn't allocate 20 MB) — it still runs ~9× realtime, ~0.3 s to
first audio for a sentence-sized chunk; **the output rate is deliberately not
configurable** and `health()` fails loudly if the service reports another format, because
a silent mismatch is heard as "the assistant talks in a high voice" with no legible cause;
and **there is no streaming *within* a sentence** — Kokoro emits one segment per sentence,
so "ilk parça" equals "toplam" in every measured row. Which adapters are real is
configuration (`MAYEN_STT`/`MAYEN_TTS`, `fake|real`, set by `baslat --stt/--tts`; defaults
fake STT, real TTS). **`MAYEN_STT=real` raises rather than falling back** — no STT model
has been chosen (§19.2), and the switch exists precisely so its absence can't read as
"STT is already real". §19.10 (voice character) carries the
legacy chain and is on; the owner has both samples to compare.

**Deferred by the owner until asked for by name (2026-08-13): `issues.md` and commits.**
Don't work on those bugs and don't commit or split the uncommitted tree. Don't propose
either as "what's next".

**Voice *input* does not work and the reason is legible.** `FakeSTT` treats the payload as
UTF-8 text, so real PCM raises `ServiceUnavailableError(… "§19.2: STT modeli seçilmedi")`.
Audio *out* works. STT stays fake by the owner's decision.

**The LLM is `Qwen3.8-27B-IQ4_XS` — §19.2's LLM half closed on 2026-08-15 by the owner's
decision, not by a measurement.** Their reasoning: public benchmarks put the 3.8 generation
ahead of 3.6, and it is the only 3.8-generation candidate on disk (no 3.8-35B exists yet),
so there was nothing to choose between. The limit is recorded with it — public benchmarks
do not measure what we measure, and "bigger is better" failed the same day on the 35B MoE.

- **This item's history is the standing lesson: a measurement is not a decision.** It read
  "closed: Qwen3.6-35B-A3B" from 2026-08-10, but the owner never made that call — an
  inference written beside the numbers hardened into a decision as it was recorded, first
  in P21 and then in every doc citing P21. Report what was measured; let the owner close.
- **Model *or prefix* change ⇒ re-measure the role text.** `config/rol.txt` was written on
  this model and re-measured on the native prefix (2026-08-16, `docs/faz-b-yerel.md`); it
  was **not rewritten** — four of golden's six failures are "asked instead of calling", and
  editing the text against them would be fitting it to the fifty.
- **§19.1 closed on 2026-08-16 with `CallFormat.YEREL`** — the owner's call. It had been
  re-read on this model the day before (2026-08-15): across four sets accuracy never
  separated CLI from JSON, and Faz 0's decisive number, first audio, had gone to a tie
  (0.22 vs 0.22). What decided it in the end was neither — a failure class the text formats
  make possible; see "Grammar and call format" below.
- **STT and TTS stay open** (owner's deferral), which is why voice *input* does not work.
- **Reports written before 2026-08-15 were measured on the 3.6 generation.** **Read
  `/props` before quoting any number as current.**

**Both known measurement gaps are now legible — read both before quoting a number:**

1. **§17.1's `uydurulan tool` counter is structurally zero** in every report, because the
   GBNF lists registry names as literal alternatives and an unregistered name is
   unproducible. That column measures the grammar, not the model — **never quote it as
   "zero hallucinated tools"**. P26 made this legible rather than fixing it: the report
   now carries the caveat next to the column, and the `halusinasyon` set measures
   production's actual failure (claiming an action, then inventing the record's content)
   through the *absence* of a call. `uydurulan argüman` has exactly one producible path —
   a flag-looking token after a list value (`cli-item`); `tests/test_agent_calls.py` locks
   it. **Every report written before 2026-08-15 lacks the caveat.**
   **In the native format the caveat no longer applies and the column becomes real**
   (2026-08-16): a JSON schema is not a grammar and the server may let an unregistered
   name through, so `from_native` raising `UnknownToolError` is the model's error, not the
   generator's. It measured zero on the first run — one run, so read it as Rule 14 says.
   The report's own caveat text still speaks only of the grammar; **the `yerel` rows are
   the exception to it.**
2. **Closed by P27 (2026-08-15), and closing it moved the numbers.** `evals` now runs two
   prefixes side by side: `Prefix.OLCUM` (the old hand-built one, kept byte-identical so
   `faz2`/`faz3` stay comparable) and `Prefix.URETIM`, which calls `build_messages`. On
   the production prefix the golden set drops 98→92 (CLI) and 98→90 (JSON) and the
   missing-argument axis collapses 100→71/57. **So every report before this date measured
   a prefix production never builds** — the format comparisons inside them are still
   valid (same prefix on both sides), but none of them says how the model does in
   production. `docs/faz6-onek.md` has the reading; two failures there (`tek-01`,
   `ser-*`) are the golden set's expectations being wrong *in production*, not the
   model's errors, and the fifty were left untouched on purpose.

### Invariants (§20) — never violate

Hard constraints, not preferences. Code that breaks one is wrong even if it works.

1. The SQLite file has exactly one owner (`mayen-core`). No other process opens it.
2. The application process loads no models. Models live in their own processes, behind interfaces.
3. The system prompt never changes within a turn. Variable content always goes at the end of the prefix.
4. Authorization lives in code. The prompt is not a security boundary.
5. Approval is never extracted from free text by keyword matching. Timeout means denial.
6. The owner tier can never be granted by voice.
7. System data (identity, policy) is never written into a user-owned text field.
8. Model output is never executed in a shell.
9. One tool is defined in one file.
10. Token counts are never estimated — ask the counter endpoint.
11. Memory and summarization work never competes with the model during an active turn.
12. Every turn is cancellable at every stage.
13. No error is silently swallowed.
14. No performance claim goes into the docs unmeasured.

### Layer layout (§4)

```
transport/   WebSocket, frame format, protocol version, backpressure
session/     Session actor and state machine
turn/        One turn: audio segment → text → agent → audio
agent/       LLM loop, tool selection, response generation
tools/       Tool registry; one module per tool
policy/      Identity → authority. Approval flow. Single authorization point.
memory/      Context window, summarization, persistent fact store
adapters/    llm, stt, tts, speaker, wakeword — all behind interfaces
data/        Repositories, schema, migrations, backup
scheduler/   Scheduled tasks and the proactive audio channel
obs/         Traces, metrics, event log, replay
```

Dependency direction is one-way: `transport → session → turn → agent → tools → adapters`.
A lower layer never imports an upper one. **If a lower layer needs something from above,
the boundary is drawn wrong — fix the boundary, don't add the import.** The fix is usually
a `Protocol` defined in the lower layer and implemented in the higher one; the codebase
does this five times (`TraceSink`, `SessionSink`, `TurnRunner`, `TurnReport`, `Conversation`).

`config.py` and `main.py` are not layers. `main.py` is the assembly: it imports everything
and nothing imports it. `evals/`, `client/` and `tests/` sit at the repo root for the same
reason — they import `mayen` and are never imported by it — and pass the same four gates.

LLM, STT, TTS and speaker recognition sit behind `Protocol` interfaces and each has a fake.
**The entire turn flow, policy and agent logic must be testable without a GPU, in seconds.**

### Enforced mechanically — don't fight these, read them

- **`tests/test_boundaries.py`** walks the AST under `src/mayen` and fails if a layer imports
  one ranked above it. Its `RANK` table is the single place the layer order is written down
  (the doc states six of eleven; the rest are derived there with reasons). Ranks are
  all-distinct — equal ranks would permit a silent cycle. The same file bans **SQL outside
  `data/`**: any string literal starting with a SQL keyword. §16's repository rule is only
  real because something enforces it.
- **`tests/test_layout.py`** names the eleven layers one by one.
- **Four gates, green at the end of every work package — not just at the end:**

```
uv sync                   # environment from the lock file
uv run ruff check .       # lint
uv run ruff format .      # format (--check in CI)
uv run mypy               # strict, over src + tests
uv run pytest             # tests
```

`ruff`'s `RUF001/002/003` (ambiguous-unicode) are off on purpose: they fire on every `ı`,
`ş`, `ğ` in Turkish docstrings.

- **Python 3.13**, pinned `>=3.13,<3.14`. The system interpreter is 3.14; the upper bound is
  what stops uv drifting onto it. **uv, not pip.** `uv.lock` is committed. Never `pip
  install` into `.venv` by hand.
- **Secrets** only from the environment via `config.load()`, wrapped in `Secret` (masked
  `repr`/`str`). `.env` is gitignored, `.env.example` is the template. Run with
  `uv run --env-file .env ...`.

### Do not undo these

Each was decided with a reason and several were bought with a bug. The full reasoning is in
`docs/PLAN.md` and in the module's own docstring.

**SQLite (P2, both verified by experiment and locked by tests)**
- Under `autocommit=True`, `Connection.rollback()`/`.commit()` are **silent no-ops** —
  `Database.transaction()` issues literal `COMMIT`/`ROLLBACK` SQL.
- `executescript` implicitly COMMITs, so migrations go through `Database.script()`.
- One connection guarded by a mutex (SQLite serializes writes anyway). The price is one
  rule: **a transaction never spans an LLM/HTTP call.** Backup opens its own connection —
  invariant 1 is about processes.

**Grammar and call format**
- **Production uses `CallFormat.YEREL` since 2026-08-16 — the model's own tool-calling
  template.** The catalog travels as JSON schema in the request's `tools` field
  (`tools/schema.py`), the server parses the call, and there is **no grammar**. The two
  text formats (CLI, JSON) are still built, still parsed, still measured — the one line
  that picks is `main.py:CALL_FORMAT`.
  **Why it changed, and it was not a score:** in a text format the branch is decided at
  the first token, so the model can either speak *or* call in one generation. When it
  wants both — "understood, setting it up; but first I need the time" — it **fakes** the
  call inside prose: nothing runs and the fake is read aloud. Banning `<` in the grammar
  did not remove the behaviour, the model wrote `[tool] date_time` instead. **Banning
  characters changes the costume, not the class.** Measured `docs/faz-b-yerel.md`:
  acceptance gate 12/15 → 14/15 (intervals overlap — not a ranking), golden 98 → 92,
  control 89 → 94, `halusinasyon` 93 → 100, `bellek` 88 → 82, argument accuracy 89 → 94.
  Four of golden's six failures are one class: the model **asked for the missing field
  instead of calling**. The fifty were not edited.
  **Two things a native-format change breaks that nothing warns you about:** the language
  rule's position (below) and any code that assumes a call is text.
- **The language rule moved to the end of the context block** (`ContextBlock.language_rule`),
  and only in the native format. Faz 7's lever inverted: the chat template inserts the
  `tools` block into the system message **after** our text, so "end of the system prompt"
  is no longer the end of the prefix. Left there, six of six hand-run turns came out
  Turkish. This does not violate Faz 7's "never put it behind the variable tail" — the
  context block *is* the variable tail and is already there; what cost 22 → 1631 prompt
  tokens was opening a **new message** after it. `main.py` decides the position, because
  main is the assembly, not a layer.
- Both grammars share the `<tool> ` prefix and prose may not start with `<`, so **the branch
  is decidable at the first token** (§6/C3). Break this and streaming buffers until the
  branch is known. This is a design constraint of the *text* formats; §19 item 4 (the
  first-audio target) is still open, so it is not a budget anyone chose.
- **No CLI value may start with `--`** (A4) **or contain `<`** (P11). Without the second, a
  model attempting a second call writes `<tool>` inside the first call's argument and
  produces a valid-but-wrong call. Price: an argument cannot contain `<`.
- **The mandatory tool mode was measured and deleted (P25). Do not re-add it without a new
  measurement.** Forcing the prefix turns the binary "is a tool needed" decision, taken
  before generation, into a multi-way "which tool" choice inside the tool branch — §6's
  design cancelled out, and there surface keywords win.
  **Re-measured on 2026-08-15 with the new role text and it lost again** — the question was
  fair (P25 ran under a role text that pushed toward calling), the answer was no:
  `halusinasyon` 73/87 → 100/100 but control 100 → 89, `bellek` 71/75 → 59/65, and the
  **missing-argument axis 86% → 14%** (`note_search --query ""`, `wake_on_lan --target ?`).
  **In mandatory mode "ask the user" does not exist as a behaviour**: `no_tool` means "no
  tool needed this turn", not "a tool is needed but I lack a field". The role text's
  precedence rule is unenforceable there — prompt and grammar contradict, and grammar wins,
  as it must. `docs/faz6-35b-zorunlu.md`.
  **Renaming the marker made it worse, and that is the reusable finding**
  (`docs/faz6-35b-tell-user.md`): `no_tool` → `tell_user` took the missing-argument axis
  14% → **0%** and the control set in JSON 89% → **0%** — 18 of 18 scenarios called a real
  tool. **A control marker must not look like a tool name.** In JSON the model expects a
  tool name to arrive inside `{"name": …}`, the grammar accepts the marker only as a bare
  literal, and facing that contradiction it stops choosing the marker at all. `no_tool`'s
  awkward negative name was load-bearing. The docstring already said a JSON costume would
  make it look like a tool; the name is a costume too.
  **The recovery patch is stale**: P26/P27 moved `evals/` and `main.py`, so
  `git apply docs/faz4/zorunlu-mod-geri-alma.patch` fails on 4 of 14 files. `src/` still
  applies cleanly; the `evals` plumbing is a hand-port (~30 min). Its header carries P25's
  numbers.
- `agent/calls.py` handles all **three** formats (`parse` for the two text ones,
  `from_native` for the native one) and `tools/` generates what each needs — two grammars
  and one schema — so a model change is a re-measurement and not a rewrite. **Nothing else
  may branch on the format**; the two places that do are `main.py`'s `CALL_FORMAT` (the
  assembly, not a layer — it also decides where the language rule goes) and `AgentLoop`'s
  constructor, which picks the grammar or the schema once.
- **`from_native` converts typed values back to text before `Tool.validate`.** The schema
  produces `{"level": 40}` as an `int`; `validate` expects text because it is the product
  of the two text formats. The measurement side bent, not `validate` — it is the single
  validation point (§9.1) and loosening it per format would split the constraint in three.

**Tools**
- The registry is an object from `tools/catalog.py:builtin_registry(config)`, **not a
  module-level global** — that is where test bleed comes from. The prompt catalog and both
  grammars are generated *from* it. Adding a tool is one file plus one line in `catalog.py`.
  It takes `config` because `app_launch`'s choices come from the app allow-list; `evals`
  passes it too, or it would measure a catalog production never builds (P27's lesson).
- **Before adding a tool, read the existing tool bodies, not just the repositories.**
  Faz 8's first list had `note_list`, `contact_list` and `contact_update` — all three
  already existed as optional arguments on `note_search`/`contact_get`/`contact_save`.
  Overlapping tools cost more than tokens: tool selection is the measured-fragile part.
- **`ArgType.ENUM` is grammar-enforced** (Faz 8): choices are literal alternatives, so an
  invalid one is *unproducible* — the argument-side twin of the tool-name guarantee, and
  it carries the same caveat (§17.1: that measures the grammar, not the model). The rule
  is per tool *and* per argument; in JSON the quotes are inside the rule or the constraint
  vanishes. `usage()` prints the choices, not `<enum>`, because the catalog is built from it.
- **An allow-list has to be visible to the model.** `app_launch` first took a `STRING`
  validated only in the body, like `wake_on_lan`. Measured on the real model it failed
  outright: asked to open the browser it answered "I have no browser configured" *without
  trying* — nothing in the catalog said which names exist. Now the names are `ENUM` choices
  from config, and with no apps configured the tool is not registered at all.
- **Effect class is per tool, never per choice.** `window_action` (DIŞ) and `window_close`
  (GERİ_ALINAMAZ, approval) are two tools for this reason: one tool would either put
  approval in front of "minimize" or let closing through without it.
- **Machine control lives behind `adapters/desktop.py`** — Wayland+KDE specifics (`wpctl`,
  MPRIS over `busctl`, KWin global shortcuts) stay there; tools know *what*, not *how*.
  X11's `wmctrl`/`xdotool` do not work here. "Switch to app X" and "list windows" are
  deliberately absent: they need KWin scripting, the shortcut path only has the active window.
- **Nothing reaches a shell** (invariant 8): argv only, and no model-written value enters an
  argv — the window action indexes a table in code, the app name indexes the config.
- `usage()` is generated from the signature, never declared beside it (§9.1's own
  doc-drifts-from-code failure).
- `ToolContext` carries repositories and one `httpx.AsyncClient`, **never a `Database`** —
  a general handle is an open invitation for SQL to leave `data/`.
- `authorize()` never looks at a tool's *name*: an exception by name is the "sensitive tool
  list" §9.1 forbids. `policy/authority.py` is the single enforcement point (invariant 4)
  and §10.2's sixteen cells are written out one by one — a generated matrix makes the test
  verify the generator's assumption. A missing cell is a `KeyError`, not a silent deny.
- `policy/approval.py` contains **no keyword matching at all** (invariant 5); it resolves
  through a three-word GBNF whose words start with different letters. An off-grammar answer
  raises rather than counting as `BELİRSİZ`.
- `contact_save` writes a new person as `BEKLEYEN` (§10.3). Name matching is **exact, never
  case-folded** — Turkish `I`/`ı` folding is wrong and a bad match edits someone else's row.

**Turn and agent**
- A malformed call is **fed back, not raised** (§8.3), and a correction **does not spend a
  step** — `MAX_ADIM` counts tools, not the model's own retries. At the ceiling the grammar
  closes the tool branch so the user still hears an answer.
- Denial and tool timeout are fed back as `ToolResult`, never raised (§8.2).
- The agent loop is a **generator**; the branch buffer is at most the call prefix, and a test
  measures exactly that.
- **State first, sentence second** (B3). Approval runs in the runner because
  `ONAY_BEKLIYOR` is a session state; a timeout **ends the turn**.
- **Cause first, state second**: an error frame goes out on §14's separate channel *before*
  the state change, or a client that saw `IDLE` would think the turn ended quietly.
- The sentence splitter is pure (punctuation + minimum length); the time threshold lives
  outside it, or punctuation rules would only be testable by advancing a clock.
- The TTS queue has no parallelism and `seq` climbs across approval and answer alike (§13).
- **Numbers with no defaults, on purpose:** `max_steps`, `min_chars`, `max_wait_seconds`,
  `approval_timeout_seconds`, `max_corrections`, `ApprovalFlow.timeout_seconds`. §19 gives
  no values; they are `main.py` constants with their reasons. A default here would be an
  open item closed by assumption.
- `turn_id` is a **uuid, not a counter** — `turn_traces.turn_id` is UNIQUE and the file
  outlives the process. Tests never saw it; the first hand-run turn did.

**Memory**
- **The context size is asked, not configured** — `LLMClient.context_size()` off `/props`.
  A config value would let the server's `-c` and the app disagree, which §11.1 forbids by name.
- A trim is never silent: every trim is a `warning` with a counter, because §11.1's real
  rule is that trimming is *exceptional*.
- Fact extraction and summarization are **one job over one batch**, so `summary_id` is the
  watermark for both.
- Background jobs are pulled when the segment **enters the queue**, not when the turn starts
  (invariant 11 / B4). The cancellation token is asyncio itself — there is no second one.
- The turn stores **two lines, user and assistant**; a barged-in turn stores no answer.

**Transport and client**
- Control frames are JSON text, audio frames binary: `[4B header length][JSON header][raw
  payload]`. Unknown type, missing field, extra field and absurd length are all
  `ProtocolError` — never ignored (invariant 13).
- **The send queue blocks when full; it never drops.** The one exception is `cancel_turn`,
  scoped to a turn so barge-in cannot drop a queued proactive reminder (B1/B2).
- Adapter streaming methods return `AsyncGenerator`, not `AsyncIterator` — `aclose()` is
  part of the contract.
- **State is broadcast, audio is not.** One turn at a time is global, so a state is true for
  the second device too. A `turn_id` that doesn't match is a late frame from a dead turn:
  dropped and logged, on **both** sides of the wire (§13).
- Neither a malformed frame nor a failing one closes the link. A segment is submitted, not
  awaited — awaiting stalls the read loop that the interrupt would arrive on (invariant 12).
- **Proactive audio is not a turn.** No state is driven; it only takes the turn's *place in
  line* via `Session.exclusive()`. Its own `turn_id` is what protects it from barge-in.
- `client/core.py` has not changed a line across four `Output` implementations (text, voice,
  GUI, fake). Adding a surface means writing an `Output`, not touching turn tracking.
- **The answer's text is its own frame** (`Reply`, protocol 2, Faz 7) — one per sentence,
  sent *before* that sentence's audio. Every client used to recover the answer by decoding
  audio chunks as UTF-8, which only worked because the fake TTS's payload was text (P1);
  the day Kokoro landed, the user saw their own question and no answer anywhere. Don't
  reintroduce payload-sniffing: real PCM partly decodes as valid UTF-8 and prints garbage.
- **A chunk boundary is not a sample boundary.** The service reads ffmpeg's output in fixed
  sizes, so an odd-length chunk arrives; PCM16 samples are two bytes and PortAudio rejects
  it. `Speaker` carries the half sample to the next chunk — dropping it shifts the stream
  by one byte and every later sample is noise. `stop()` drops it.
- **`Client.run()` reports a failing frame instead of dying on it** (Rule 13). It used to
  catch only `ConnectionClosed`: one speaker error killed the read task, nothing reached
  the screen, and the client went **silently deaf** — the user typed and nothing happened.
  The one-byte bug was the fault; this is what kept it invisible.
- **The GUI's speaker is opt-in** (`--gui --ses`); without it the window only writes.
- The client is **half duplex** until real AEC — no echo cancellation means every answer
  would interrupt itself. `--soz-kesme` reverses it. This is a state, not a decision.
- Barge-in fires at the **start** of speech, not the end of the segment.
- `stop()` uses PortAudio's `abort()`, not `stop()`: making a cancel audible means *not*
  playing what is queued (§13).

**Measurement (`evals/`)**
- Every ratio carries a **Wilson 95% interval**, and two runs with overlapping intervals are
  not a ranking. Wilson rather than the normal approximation because the region of interest
  is near the ends.
- **The 50-scenario golden set is untouched** so `docs/faz2-olcum.md` stays comparable. New
  work adds a set, never edits the fifty.
- Tool bodies are not run — network and DB would make the measurement non-deterministic.
- No judge model: a judge's own hallucinations would enter the measurement. That is why
  §17.1's third counter is the narrow, mechanical "unsupported numbers".
- A zero means "none in the measured slice", not "none" (Rule 14). Report the denominator.
- **A prompt rule's *position* is a lever, and the role text is the weakest position**
  (Faz 7, `docs/faz7-rol.md`). §2's "output English" was written into `config/rol.txt` three
  measured times — in Turkish, then in English, then with the `Administrator` anchor back —
  and never took: 18 control answers, ~2 English. The Turkish input, history and catalog
  outweigh one instruction at the *front* of the prefix. The identical sentence moved to the
  **end of `system_prompt()`, after the catalog** gives **18/18**. So: before rewriting a
  role text a fourth time, ask whether the rule is in the wrong *place*. The rule lives in
  `config/dil-en.txt` via `MAYEN_LANGUAGE_RULE_PATH`, not inside the role text.
- **§8.1's "variable content last" also forbids putting a *constant* after it** — being
  fixed is not an exemption, being behind the variable tail is what costs. Measured: the
  same language rule as a trailing message after the user's sentence works for language but
  collapses prompt-cache reuse — per-scenario prompt tokens **22 → 1631**, TTFT **0.24 →
  1.04**, every set, every format. Read `llama-server`'s own `timings.prompt_n` before
  theorising about latency; that is what identified it as prefill rather than generation.
- **Writing the persona as "report the situation like a ship's computer" pushed the model
  into the third person** and it leaked its own role text and JSON schema keys (`name`,
  `arguments`) into quoted prose — the `desteksiz alıntı` counter caught it. The fix was a
  principle, not a ban: *speak to the Administrator, never about them; write only what you
  say out loud.* Counter went to zero everywhere.
- **`config/rol.txt` was rewritten in three measured turns and adopted on 2026-08-15**
  — **superseded by Edden on 2026-08-16**, but every lesson below still holds and Edden
  keeps all four of its behavioural paragraphs byte-identical; the superseded text is
  verbatim in `docs/faz7-rol.md` —
  (`docs/faz6-27b-rol3.md`, on 27B: golden 100/96, control 100/100, `halusinasyon` 93/100,
  `bellek` 94/94 — the previous text was 98/96, 94/89, **73/87**, 100/100). Three things it
  cost to learn, all still true of the next edit:
  1. **This failure class does not respond to prohibition.** Turn 1 wrote "say you did it
     only after seeing the result" and `halusinasyon` fell 73→40: the model isn't breaking
     the rule, it believes the conversation already supplied the knowledge, so it skips the
     call and invents in *more* detail. Teach the missing **distinction** (what was *said*
     is a claim; a tool result is knowledge), not the ban.
  2. **Two general principles at the same level means the model picks one.** Turn 2 got
     `halusinasyon` to 100/100 and lost golden and `bellek` — all of it "asked to ask, called
     instead". Turn 3 changed nothing but made the missing-field check a **precondition** of
     calling and wrote the precedence down.
  3. **Stop while the remaining gap is one or two scenarios.** A fourth turn would have been
     fitting the text to the fifty.
  Rejected and superseded texts are verbatim in `docs/faz6-rol.md` and `docs/faz6-27b-rol.md`.
  **It was then checked on the weak model too** (`docs/faz6-35b-rol3.md`): the morning's
  collapse is gone (33/53 → **73/87**), so the distinction bought robustness, not just a
  better score. Its residual cost is one class — calling when no tool was needed (`bellek`
  71/76 there, two scenarios on 27B). That is the trade to keep: **an unnecessary call is
  latency; "yes, I set it up" is `issues.md`.**
- **A role-text result is only valid for the model it ran on, and the A/B runs all four
  sets.** The failure class a prompt edit opens shows up in the set you did not target — the
  2026-08-15 morning A/B ran only golden + control and missed a collapse. The same text
  scored 73/87 on 27B dense and 33/53 on the 35B MoE. §19.2 is open, so the role text is not
  settled either; re-measure when the model changes.
- **The 35B is `Qwen3.6-35B-A3B`, a MoE with 3B active — expected to be *weaker* than the
  27B dense**, and no 3.8-generation 35B exists yet. So "the adopted text costs `halusinasyon`
  on 35B" reads more sharply as: **the text holds on a strong enough model and breaks when
  the model weakens.** A role text that measures well is not thereby robust.
- **A set's expectations go stale when the catalog grows** (Faz 8). Adding `volume` dropped
  `kontrol` 100 → 94 in both formats, and the single flipped scenario is `kon-08`
  ("Sesini biraz kısabilir misin?"), marked `TOOL_GEREKMEZ` back when no volume tool
  existed. The model is right and the scenario is wrong. It was **left untouched** for the
  same reason the fifty are: fitting a set to the result turns the measurement into a test
  of its own assumption. Read a control regression against what the catalog gained.
- **Two prefixes, and the report says which** (P27): `--onek olcum` is the historical one,
  `--onek uretim` builds production's messages through `build_messages`. Pass both to get
  them side by side in one report — separate files can't show they ran the same day on the
  same server. The `bellek` set forces `uretim`; its summary/fact blocks have nowhere to go
  in the old prefix.
- **One call format by default** (Faz C, `--bicim`, default `main.py:CALL_FORMAT`). The runner
  used to sweep all three; once §19.1 closed, that tripled every run for two dead paths. The
  text formats were **not deleted** — the owner's call, "keep them aside but not active" — so
  they are still generated, parsed and tested, and `--bicim cli --bicim json` brings them back
  for a model change. In `evals/session.py` the second arm is `--metin-kolu`, off by default
  and **it must stay off**: with `CALL_FORMAT` native it hands `parse()` the native format,
  which `calls.py:145` calls a code error, so the arm emits no call and **its score is not a
  measurement** — it was once reported as 1/15 before that was noticed.
- **`--ornekleme {greedy,sunucu}`.** `greedy` stays the default because every number since
  `docs/faz2-olcum.md` was read under it. `sunucu` reads the settings off `/props` and still
  **sends** them — the value comes from the server, the transmission stays explicit, so the
  door closed against a server flag deciding silently stays closed. Needed for a model tuned
  to its own temperature/penalties (LFM2.5).
- **The `halusinasyon` set does not measure production's history** (`evals/runner.py:226`, on
  purpose): its fixtures are `tool=None`, so the past turn carries no tool result. Single-turn
  sets still measure the world before the 2026-08-16 fix; fabricating results would make the
  measurement validate its own assumption. **For a verdict about production behaviour the
  instrument is the acceptance gate** (`evals/session.py`). Faz C: the same model scored 33%
  on the set and 80% at the gate, and the reading is *healthy state indistinguishable; after
  one fabrication the 27B recovers and the 35B compounds*.
- Run: `uv run --env-file .env python -m evals --model <ad> --kume <küme> --out docs/<ad>.md`

### Settled §19 items you will need while coding

- **App allow-list: a TOML config file**, `MAYEN_APPS_PATH`, `[apps]`, name → argv **array**
  (a single string would need shell splitting, which is where escaping leaks). Names are
  validated at load against the same narrow pattern `ENUM` choices must match, because they
  become grammar literals. Same shape and same reason as `wol.toml`.
- **Weather: OpenWeatherMap** (§19.7). Key from the environment, **never committed**.
  Quota and key errors are surfaced, not swallowed (§14).
- **Course schedule: a file in the repo** (§19.8), loaded into the DB at startup.
- **Wake-on-LAN targets: a TOML config file** (§19.9), `MAYEN_WOL_TARGETS_PATH`, `[targets]`.
  MACs validated at load; an unreadable path is a `ConfigError`, never an empty list. The
  tool **refuses raw MAC addresses** — a model-spoken address would reach a device outside
  the list.
- **Owner assignment: a CLI setup script** (§19.14). Invariant 6 holds: the path to owner
  has no voice door, only a shell door requiring physical access. Same reasoning as
  `MAYEN_ASSUME_OWNER`, the temporary flag that makes every segment `SAHİP` while §19.3's
  thresholds are unmeasured — it warns at startup and mints **no `person_id`**, and it is
  deleted when speaker recognition becomes real.
- **Qt binding: PySide6** (§19.11), optional `gui` extra. `sounddevice` is the `voice` extra.

### Still open — do not substitute assumptions

`ARCHITECTURE.md` §19: **item 2's STT half (deferred by the owner; the LLM half closed
2026-08-15, the TTS half 2026-08-16)**, 3–6, 12–13, 15. Item 10 (voice character) is
answered in code by the legacy effect chain but the owner has not said the word; **15
(Turkish proper nouns through the English voice) is now measurable and still unmeasured.**
Blocking map at the end of `docs/PLAN.md`.

**Two of those are open *by scope*, not for want of a measurement — do not propose a number
for either** (Faz C, 2026-08-17, `docs/faz-c-model-taramasi.md`). **§19.4 (first-audio
target):** the owner declines a threshold on purpose — "if I say 3 seconds and we get 3.1, I
don't want to chase 100 ms." A threshold manufactures an obligation, and this is an MVP.
**STT:** not needed yet, and the hardware (GPU/VRAM/model) may change; binding a model choice
to something that will change is the thing being avoided. Both were proposed a number in Faz C
and both were declined with reasons. Measure and report; the scope is the owner's.

Undecided in code, deliberately: **barge-in during `ÇÖZÜMLÜYOR`** still raises — there is no
audio to cut before the segment has become text, and closing one gap in §5's table does not
license closing the other for symmetry. **Wake word** (§19.6) and **AEC** (§18 calls it the
phase's largest item) are unwritten. **Voice-profile save/delete** needs §19.3's thresholds.
None of these were closed by assumption; don't close them now.

### Conventions

- `docs/ARCHITECTURE.md` is Turkish; keep it that way when editing it.
- **Naming — two languages, split by role:**

  | What | Language | Example |
  |---|---|---|
  | API names: modules, classes, functions, parameters, locals | English | `configure`, `LLMClient` |
  | Domain vocabulary — state and effect-class **values** | Turkish, as in the doc | `State.ONAY_BEKLIYOR` |
  | Docstrings and comments | Turkish | — |
  | Test names | English | `test_context_fields_reach_output` |

  Domain vocabulary stays Turkish so it matches `ARCHITECTURE.md` one-to-one — a translation
  layer between doc and code is where drift starts. **Identifiers carry no Turkish
  diacritics** (`ONAY_BEKLIYOR`, not `ONAY_BEKLİYOR`): `.upper()`/`.lower()` are wrong for
  Turkish `İ`/`ı`, so any case-folding on them silently misbehaves. The accented form belongs
  in the enum's string *value* and in user-facing text, never in the symbol.
- Tool definition, body and policy class live in the same file (invariant 9).
- Tools reach data only through the context object, never a global DB handle.
- Tool results are structured: success flag, data, human-readable form and error are
  separate fields. Not "everything is a string, parse the JSON twice."
- **Repositories return frozen dataclasses, never `sqlite3.Row`** — a `Row` leaks column
  names upward and makes a schema rename break tool bodies.
- **Timestamps are ISO-8601 UTC strings** from `data/clock.py` — one format, one place
  (`clock.FORMAT`/`clock.parse()`). Two modules writing two formats is a broken sort nobody
  notices.
- **Stored vocabulary lives in `data/`**, not in the layer reasoning about it: `Tier` in
  `data/repositories/people.py`, `TaskStatus` in `tasks.py`, because the CHECK constraint
  already owns those words. `policy` imports them; the reverse breaks §4.
- **Never `git commit`.** Write the commit message as text and let the owner commit it.
  Style: Turkish, passive voice (`eklendi`, not `eklenir`), conventional-commit prefix, short.
