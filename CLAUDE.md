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

### Current state

**P1 and P2 are done (2026-08-09); P3 — protocol, adapter interfaces, fakes — is next.**
See `docs/PLAN.md` for all three.

`src/mayen/` holds the eleven §4 layer packages. Real so far: `obs/log.py` (structlog),
`config.py` (typed env config + `Secret`), and all of `data/` — `db.py`, `migrate.py`,
`clock.py`, `backup.py`, `migrations/001_initial.sql`, and eight repositories under
`data/repositories/`. Still empty: `transport/`, `session/`, `turn/`, `agent/`, `tools/`,
`policy/`, `memory/`, `adapters/`, `scheduler/`.

**Two SQLite traps P2 hit, both verified by experiment and locked by tests.** Do not
undo either:

1. Under `autocommit=True`, `Connection.rollback()` and `.commit()` are **silent no-ops**.
   `Database.transaction()` issues literal `COMMIT`/`ROLLBACK` SQL for that reason.
2. `executescript` implicitly COMMITs any pending transaction, so it cannot run inside
   `transaction()` — migrations go through `Database.script()`, which puts the transaction
   control inside the script itself.

**Concurrency:** one connection, guarded by a mutex. Writes serialize in SQLite anyway
(one writer even in WAL), so extra connections buy nothing and turn lock waits into
`SQLITE_BUSY`. The price is one rule: **a transaction never spans an LLM/HTTP call.** Open,
read or write, close. Backup opens its own connection — invariant 1 is about processes.

- **Python 3.13**, pinned `>=3.13,<3.14` in `pyproject.toml` and `.python-version`. The
  system interpreter is 3.14; the upper bound is what stops uv drifting onto it. torch,
  ctranslate2 and onnxruntime all ship cp313 wheels — verified before pinning, per P1.
- **uv**, not pip. `uv.lock` is committed. Never `pip install` into `.venv` by hand.

Commands — all four must be green before P1 is done:

```
uv sync                   # environment from the lock file
uv run ruff check .       # lint
uv run ruff format .      # format (--check in CI)
uv run mypy               # strict, over src + tests
uv run pytest             # tests
```

`ruff`'s `RUF001/002/003` (ambiguous-unicode) are disabled on purpose: they fire on every
`ı`, `ş`, `ğ` in Turkish docstrings and are pure noise here.

**`tests/test_boundaries.py` enforces §4 mechanically.** It walks the AST of everything
under `src/mayen`, extracts `mayen.<layer>` imports, and fails if a layer imports one ranked
above it. The `RANK` table is the single place the layer order is written down; the doc
states only six of the eleven, the rest are derived there with reasons. Ranks are
deliberately all-distinct — equal ranks would permit mutual imports, i.e. a silent cycle.

If this test blocks an import you want, **the import is not the fix.** Either the boundary
is drawn wrong, or the dependency needs inverting (define a `Protocol` in the lower layer,
implement it in the higher one). `obs` sitting at the bottom will hit exactly this in P3.

**Secrets:** only ever from the environment, via `config.load()`, wrapped in `Secret` —
whose `repr`/`str` are masked so a key cannot leak into a log field or traceback. `.env` is
gitignored, `.env.example` is the committed template. Run with `uv run --env-file .env ...`.

### What it is

A voice assistant. Turkish speech in, English speech out. Single machine, local models
only, owns its own data. Single owner, plus other people who may speak to it with limited
privileges.

First-release capabilities: weather, date/time, contacts, notes, course schedule, system
metrics, Wake-on-LAN, reminders/scheduled tasks.

Out of scope: multi-user accounts, remote/internet access, cloud models.

### Source of truth

`docs/ARCHITECTURE.md` is the foundation. It is written in Turkish and every decision in
it is explicit. Read it before proposing anything structural.

Its own meta-rule (§19): **items marked AÇIK (open) are not implemented until answered.
Assumptions are never substituted for them.** If a task depends on an open item, say which
one and stop — don't pick a default.

### Invariants (§20) — never violate

These are hard constraints, not preferences. Code that breaks one is wrong even if it works.

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

A lower layer never imports an upper one. If a lower layer needs something from above, the
boundary is drawn wrong — **fix the boundary, don't add the import.**

LLM, STT, TTS and speaker recognition sit behind `Protocol` interfaces and each has a fake.
The entire turn flow, policy and agent logic must be testable without a GPU, in seconds.

### Architecture review — closed 2026-08-06

An inconsistency review of `ARCHITECTURE.md` produced eleven findings. All are now folded
into the doc; this list records **why those passages read the way they do**, so nobody
"fixes" them back.

- **Mid-conversation budget overflow** (§11.1 said summarize, §11.2 said never summarize
  during a conversation). Resolved: **hard trim, then summarize at the first idle moment.**
  Trimmed messages leave the context window but are never deleted from the DB. Invariant 11
  is preserved — no background job competes with an active turn. The gap between trim and
  summary is covered by the persistent fact store (§11.3), not by the summary. Trimming is
  an exceptional event; its frequency is measured, and frequent trimming means the budget is
  wrong, not that the trim strategy needs tuning.
- **Authority tiers**: four, not three. §2 corrected to match §10.2.
- **Speaker-recognition model**: its own process, behind HTTP, on **CPU**. Invariant 2 is not
  weakened by an exception. Four model services exist, not three; VRAM stays with the
  LLM/STT/TTS trio.
- **CLI-style parsing rule** (§8.3): any field may be multi-word and is read until the next
  known flag; at most one field may contain flag-like text, and it sits last in the
  signature. The old "only one free-text field" wording contradicted §9.2's own example.
- **Phase ordering**: tool *declarations* moved ahead of Phase 0 (it needs the catalog);
  a minimal headless client moved into Phase 5 (its done-criterion needs one).
- **`turn_id` on every audio frame** (§13). Without it, a late frame from a cancelled turn is
  indistinguishable from the new turn's first frame. Cancellation is scoped to a turn, not to
  the queue — which is also what keeps a barge-in from silently dropping a queued proactive
  reminder (§12).
- **`ONAY_BEKLİYOR` is entered before the approval sentence is read out** (§5, §8.5). Barge-in
  during the read-out stops audio but preserves state and the pending plan; the segment goes
  straight to the approval resolver. Safe because the resolver is constrained output —
  invariant 5 is untouched.
- **Background LLM jobs are preemptible** (§11.3): they carry a cancellation token and are
  killed the moment a turn enters the queue. Partial results are not written.
- **Server has no `DİNLİYOR` state** (§5). With client-side endpointing, the server goes
  `IDLE → ÇÖZÜMLÜYOR` on a completed segment. `DİNLİYOR` belongs to the client.
- **One turn at a time is global**, not per device actor.
- **The GBNF grammar must make the tool-call vs prose branch decidable at the first token**
  (§6). Otherwise streaming buffers until the branch is known and the first-audio latency
  budget is spent there. This is a grammar design constraint, not a later optimization.

### Settled §19 items you will need while coding

- **Weather: OpenWeatherMap** (§19.7). A developer key exists. It is read from the
  environment/config and **never committed** — this is the system's first secret, so secret
  handling is set up once in P1. Quota and key errors are surfaced, not swallowed (§14).
- **Course schedule: a file in the repo** (§19.8), YAML/TOML, loaded into the DB at startup.
  It changes once a semester; no runtime editing surface.
- **Wake-on-LAN targets: config file** (§19.9), name → MAC. No table, no CRUD tools.
- **Owner assignment: a CLI setup script** (§19.14). Collects a few voice samples, marks the
  profile as owner, refuses to run if an owner already exists. Invariant 6 holds — the path
  to owner has no voice door, only a shell door that requires physical machine access.

### Still open — do not substitute assumptions

`ARCHITECTURE.md` §19, items 1–6 and 10–13, 15. Blocking map is at the end of
`docs/PLAN.md`. **Nothing open blocks P1–P8**; everything remaining belongs to Phase 2 or
later. Closed items keep their numbers and are marked ✅ in place, so cross-references stay
valid.

AEC is nominally a Phase 5 line item but is that phase's largest piece of work; the
half-duplex escape hatch (muting the mic while speaking) kills barge-in entirely.

### Conventions

- `docs/ARCHITECTURE.md` is Turkish; keep it that way when editing it.
- **Naming — decided 2026-08-09.** Two languages, split by role:

  | What | Language | Example |
  |---|---|---|
  | API names: modules, classes, functions, parameters, local variables | English | `configure`, `get_logger`, `LLMClient` |
  | Domain vocabulary — state and effect-class **values** | Turkish, as in the doc | `State.ONAY_BEKLIYOR`, `Effect.GERI_ALINAMAZ` |
  | Docstrings and comments | Turkish | — |
  | Test names | English | `test_context_fields_reach_output` |

  The domain vocabulary stays Turkish so it matches `ARCHITECTURE.md` one-to-one — a
  translation layer between doc and code is where drift starts. Everything else is English
  so the code doesn't alternate languages mid-line around `structlog`, `httpx`, `pytest`.

  **Identifiers are written without Turkish diacritics** (`ONAY_BEKLIYOR`, not
  `ONAY_BEKLİYOR`). Turkish `İ`/`ı` are valid in Python identifiers but `.upper()`/`.lower()`
  are wrong for Turkish, so any case-folding on them silently misbehaves. The accented form
  belongs in the enum's *string value* and in user-facing text, never in the symbol.
- Tool definition, body and policy class live in the same file (invariant 9). Adding a tool
  means creating one file and registering it. Nothing else is touched.
- Tools reach data only through the context object handed to them, never a global DB handle.
- Tool results are structured: success flag, data, human-readable form and error are
  separate fields. Not "everything is a string, parse the JSON twice."
