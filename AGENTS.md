# Agent Guidelines

This file holds instructions specific to AI coding agents working in this repo.
Project architecture, data conventions, and workflow rules live in `CLAUDE.md` —
read that first; this file only adds agent-behavior rules.

## Be judicious with subagent use

Spawning subagents (background research agents, parallel workers, multi-agent
workflows) costs tokens, time, and review effort. Default to doing the work
inline.

**Good reasons to spawn an agent:**
- Web research fan-out where several independent search tracks genuinely run in
  parallel (e.g., one agent on CWA enforcement cases, one on non-CWA water
  disputes) and the results come back as structured data to verify.
- A long-running task that would otherwise block interactive work.
- A broad read-only codebase sweep where only the conclusion matters.

**Don't spawn an agent for:**
- Anything answerable with one or two searches, file reads, or a grep.
- Work you're about to do anyway in the same session (duplicated effort).
- Small edits, single-source verification, or tasks needing this session's
  context to judge correctly.

**Rules of thumb:**
- Two or three well-scoped agents beat a fleet; give each a tight prompt,
  an explicit dedupe list, and a structured output format.
- Verify agent output before committing it — spot-check claimed sources
  (URLs, case numbers); agents can return stale or unverifiable claims.
- Never let a subagent write to the dataset or commit; integration stays in
  the main session where the schema and tests are in context.
