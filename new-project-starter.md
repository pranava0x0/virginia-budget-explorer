# Starting a new project — what to copy from here

`~/Projects/coding-best-practices/` is the canonical base. When you spin up a new project, copy the *base rule files* and extend them; create the *living files* fresh; leave the *folder-internal* files behind.

## Copy and extend

| File | Copy? | Note |
| --- | --- | --- |
| `CLAUDE.md` | **Yes** | The *what*. Copy verbatim, then append a project-specific "Project intent" + file map + schema notes at the top. Project rules win on conflict. |
| `AGENTS.md` | **Yes** | The *how*. Copy, then add the project's concrete verify commands, file map, and conflict cheatsheet. |
| `DESIGN.md` | **Only if it has a UI** | Copy for any web frontend. Skip for a pure CLI, library, or data-pipeline project with no rendered surface. |

## Create fresh (don't copy — they're per-project living state)

- `backlog.md` — start empty; add ideas as they appear.
- `issues.md` — start empty; the bug audit trail.
- `security.md` — start with today's date + an empty advisory log. Refresh on the targeted triggers (new project / install / CDN asset / Action / fetched script) per CLAUDE.md.
- `data-sources.md` — only if the project fetches external data; logs exhausted/walled seams so no agent re-confirms a dead end.
- `README.md` — project-specific.

## Do NOT copy

- The topic-split files (`architecture.md`, `frontend.md`, `error-resilience.md`, `python.md`, `testing.md`, `git.md`, `networking.md`, `data-handling.md`, `ai-and-apis.md`, `project-management.md`, `security.md` *as a topic doc*). These are this folder's own reference index — they mirror `CLAUDE.md` sections and would just drift. The project gets its rules from the copied `CLAUDE.md`.
- `sources/`, `proposed-improvements-*.md`, `docs/new-project-starter.md` — folder-internal working docs.
- `MEMORY.md` / `memory/` — auto-managed by Claude Code per project; don't hand-copy.

## One-liner

```sh
# from the new project root
BASE=~/Projects/coding-best-practices
cp "$BASE/CLAUDE.md" "$BASE/AGENTS.md" .       # + DESIGN.md if it has a UI
printf '# Security advisory log\n\nLast updated: %s\n' "$(date +%F)" > security.md
: > backlog.md ; : > issues.md
```
