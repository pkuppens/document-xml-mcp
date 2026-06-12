# AGENTS.md — Agentic Development Workflow

This file documents the way we work with AI agents (Claude Code) on this project.
It captures what worked well so every future session starts with the same quality.

---

## Core Loop

```
PLAN → TASK → IMPLEMENT → VALIDATE → COMMIT → NEXT TASK
```

Every unit of work follows this loop without exception.
No task is marked done until validation passes.
No commit is made until the task is fully validated.

---

## Planning

1. Start with a **PLAN.md** at the repo root.
2. Each milestone is a heading; each task is a subsection with a self-contained **prompt block**.
3. Prompt blocks are written so they can be handed verbatim to an agent in a fresh session — no implicit context required.
4. Tasks are ordered so each one depends only on what was built before it.
5. Review PLAN.md before implementation begins. Adjust scope, split tasks, or reorder if needed.

---

## Task Tracking

Use the built-in task tool (`TaskCreate`, `TaskUpdate`, `TaskList`) to track every task:

- Create all tasks upfront so progress is visible.
- Mark `in_progress` before touching any file.
- Mark `completed` only after validation passes and the commit is made.
- Never batch completions — mark each task done the moment it is finished.

---

## Implementation Rules

- **One task at a time.** Finish and commit before starting the next.
- **No scope creep.** If a discovery warrants extra work, create a new task — do not expand the current one silently.
- **No placeholders.** Every file written must be real, runnable code.
- **Prefer editing existing files** over creating new ones unless the task explicitly requires a new file.
- **No comments that describe what the code does** — only comments that explain non-obvious *why*.

---

## Validation Gate

Run this before every commit. All checks must pass:

```bash
uv run ruff check src tests        # lint
uv run ruff format --check src tests  # format
uv run mypy src                    # type check
uv run pytest                      # tests
```

If any check fails: fix it, re-run, then commit. Never commit a failing state.

---

## Commit Convention

One commit per task. Message format:

```
#<issue>: <type>: <one-line summary>

Validation:
- ruff check: <result>
- mypy src: <result>
- pytest: <N> passed [, <coverage>%]
- <any notable fix or decision made during the task>
```

Types: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`.
Always reference the issue number even if no GitHub issue exists (use the PLAN.md task number).

---

## Logging Convention

| Layer | Level |
|-------|-------|
| MCP tool entry / exit | `INFO` |
| Service `process()` start / done | `INFO` |
| All internal steps | `DEBUG` |
| Rejections (security, validation) | `WARNING` |
| Unhandled exceptions | `WARNING` with `exc_info=True` |

- Default log level: `DEBUG` (change via `XML_PROCESSING_LOG_LEVEL` env var).
- Never log document content; log sizes, counts, and first bytes only.
- Error messages must be actionable: include the received value and a hint at the likely fix.

---

## Error Handling at Tool Boundaries

MCP tools must never raise unhandled exceptions to the caller.
Wrap the entire tool body in `try/except`, return errors as `warnings: [str(exc)]` in the response model.
Log the full traceback with `exc_info=True` at `WARNING` level so it is visible in server logs.

---

## Architecture Invariants

Keep these true at all times:

- Pipeline shape: `Source → Parser → DocumentTree → Renderer → Sink`
- Each layer depends only on an **abstract Protocol**, never a concrete class.
- Security checks (`check_file_size`, `check_extension`, `safe_open_docx`) always run before parsing.
- File paths are always validated against an explicit allow-list using `Path.resolve()` + `is_relative_to()`.
- No layer writes to disk except `FileSink`.
- No layer makes network calls (parsing is fully offline).

---

## Debugging Checklist

When a tool returns an unexpected error, check the server log in this order:

1. **Tool entry log** — were the inputs logged as expected? Check `filename`, `path`, `base64_len`.
2. **`Base64Source` first_4_bytes** — ZIP magic bytes are `b'PK\x03\x04'`. Anything else means corrupt base64 (e.g. macOS newlines — pipe through `tr -d '\n'`).
3. **`FileSource._validate`** — compare logged `resolved` path with `allowed_dirs`. Client paths are meaningless to the server; the server resolves from its own working directory.
4. **`safe_open_docx` entry log** — confirms bytes arrived intact.
5. **Exception log** — `WARNING` lines include full `exc_info` traceback.

---

## What Made This Session Work

- **PLAN.md first.** Writing prompts before coding forced clarity on scope and order.
- **One task, one commit.** Context never grew stale; rollback is always clean.
- **Validate before commit, not after.** Caught issues (import order, Rule 3 over-promotion, ZIP bomb test) within the same task rather than carrying them forward.
- **Tests as the contract.** Tests were written alongside implementation, not after. Coverage gaps were immediately visible.
- **Fixes documented in commit bodies.** The Rule 3 `_NON_PROMOTABLE` fix and the ZIP bomb test approach are recorded where they belong — in the git log.
