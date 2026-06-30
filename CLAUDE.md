# CLAUDE.md: Universal Development Principles

> Base file for every project in this folder. Project files extend it and win on conflict (they're the local source of truth).
>
> Companion files: [AGENTS.md](AGENTS.md) is the *how* for agents; [DESIGN.md](DESIGN.md) is the *look*.

---

## North star: ship small things that work end-to-end

One rule drives the rest: **build the smallest version that works, then add only what the next real user need demands.** (Karpathy: "make it work, then make it good." levels.io: "ship it ugly, ship it now.") A working ugly thing teaches more in a day than a plan teaches in a month.

- **No half-finished work.** A feature ships end-to-end or stays a branch, never merged 80% done with a TODO.
- **No speculative abstraction.** Three similar lines beat a premature helper. Build the helper the second time you need it.
- **No future-proofing without a present user.** Every config knob, plugin point, and flag is dead weight until someone uses it.

---

## Agent Workflow: Explore → Plan → Code → Verify

Never blindly write code.

1. **Explore.** Find relevant files and understand existing patterns before touching anything.
2. **Plan.** Assess blast radius. For significant changes, present 2–3 approaches with pros/cons and get approval before coding.
3. **Code.** Implement following the rules below.
4. **Verify.** Run tests, use the feature, fix all failures before declaring done.

**Read before edit**, always, even if you read the file earlier this session. **Ask for options first** on non-trivial tasks; the first plausible plan is rarely the best. **Close the loop yourself**: build so the agent can compile, lint, test, and verify its own output. (Karpathy: "agentic coding works when the eval is the loop.")

---

## Communication style

- **Concise.** No filler, apologies, moralizing, or generic advice.
- **Show your work** only when it changes the answer.
- **Fail loud.** No catch-all handlers that swallow errors. Raise or log.
- **State results, not effort.** "Tests pass," not "I worked hard to get tests to pass."

---

## Architecture principles

- **No over-engineering.** Only changes directly requested or clearly necessary.
- **Boring tech wins.** Vanilla JS, SQLite, static HTML, system fonts, plain Python beat the framework-of-the-month. Every dependency is a future bug, migration, and advisory. (levels.io: "boring tech is the secret.")
- **Single source of truth.** Constants, configs, shared types derive from one place. If a value is duplicated, test that the copies match.
- **Modular layers.** Data fetching, processing, storage, presentation: distinct modules.
- **Idempotent operations.** Re-running is safe (`INSERT OR IGNORE`, cache checks, dedup by key), but that protects re-runs, not concurrent writers. Never run two instances of the same stage on overlapping inputs; both writing one output dir corrupt each other.
- **Precompute derived values at ingest, not per call.** Compute a hot-loop value (e.g. a per-record search string) once at write time and store it. No per-call fallback that re-derives it, that silently defeats the optimization; prefer "no key → no match" so a missed index fails loud.
- **Static when possible.** Baked data over runtime backends. A `docs/` folder on GitHub Pages beats a server to babysit.
- **Cost-optimized.** Free tiers; cheapest resource that meets the requirement.
- **CLI-first.** Build CLI entry points before UI so agents can self-validate output.
- **Minimize page weight and request count.** Content sites stay lightweight: fewest requests, smallest payload.
- **Tree-shake and code-split.** Lazy-load what a page needs; don't bundle every controller everywhere.
- **Benchmark against best-in-class.** If the simplest site in the org is orders of magnitude lighter, review the build.
- **Document subsystems.** A `docs/` folder noting non-obvious subsystems, decisions, and correct CLI invocations. One line prevents repeated mistakes.

---

## Error resilience

- **Never let one item crash the pipeline.** Wrap per-record processing; log and continue.
- **Log aggressively:** every request, parse, API call, cache hit/miss, filter decision.
- **Cache everything fetchable** so re-runs are fast and cheap.
- **Validate everything.** Invalid external responses → log and skip, never crash.
- **Track errors visibly** in `issues.md` or an errors array. Failures must surface.
- **Checkpoint long jobs incrementally.** Save per unit, commit per N units / per partition, and log every failure to an append-only `ingest_log.jsonl` with a `retryable` flag. End the run with a one-line status report (`✓ N done · ✗ M failed (reason) · → resume at X`). A job that only reports success hides the items that silently fail every re-run.
- **Resume/backfill merges with on-disk output.** A `--missing-only` run must merge new records with existing *before* writing, or a capped partial run drops everything done earlier. Keep a progress manifest (per partition: `last_run`, `count`, `next_target`) so a new session resumes without re-deriving progress. Distinguish a closeable gap from a permanent source-side dead-end. Don't re-run enrichment for data upstream will never give; mark it a known structural gap.
- **Re-run a nondeterministic stage on failed records only, never blind-rebuild a validated corpus.** OCR, some PDF text extractors, and LLM passes don't return identical output twice; a whole-corpus re-structure drifts already-good records (one blind re-run dropped a validated report from 12 findings to 1). Make any recovery/backfill pass *additive and gated*: run it only where the primary path produced nothing, so the diff touches only the recovered ids and validated records can't regress. Process pathological-size inputs individually: a batch pipeline OOM-kills on the largest item and silently loses the rest of the batch.
- **Verify files are really on disk before debugging a "code" bug.** Cloud-sync (iCloud / Dropbox / OneDrive) can leave dataless placeholders that read empty / NUL while the inode reports the right size, and `git status` calls them *clean* because it trusts its stat-cache and never reads the bytes. The symptoms masquerade as code bugs (`ERR_INVALID_PACKAGE_CONFIG`, every route 500s, multi-minute boots, `page 2.tsx` conflict-copies). Fix: delete the file *then* `git checkout` (a plain checkout no-ops on a "clean" placeholder); better, move the repo out of the synced folder.
- **Key file-backed caches on a signature, not a TTL.** For a cache fronting a local file, key on `(mtime_ns, size)` instead of a fixed `ttl=`; it busts the instant the file changes and serves indefinitely otherwise. A time-based TTL either serves stale data or churns needlessly.

---

## Security & credential handling

- **Never commit secrets.** Read credentials from env vars only; halt with a clear error if missing; never log them.
- Always `.gitignore`: `.env`, `.env.local`, `credentials.json`, `secrets/`, `node_modules/`, `__pycache__/`, `dist/`, `*.pyc`.
- Before committing: `git diff --cached | grep -iE "apikey|password|token|secret"`.
- **Respect privacy choices.** Don't proxy tracking SDKs through your own domain to dodge blockers.
- **Check the security advisory index before risky supply-chain actions, targeted, not on every command.** Supply-chain attacks hit popular packages within hours of a maintainer phish. Fetch the advisory index at `https://pranava0x0.github.io/vibe-coding-security/llms-ctx.txt` (~12 KB) and surface any match **before** these specific actions: (1) starting / scaffolding a new project, (2) any `npm install` / `pip install` / `uv add` / dependency add or upgrade, (3) adding a third-party CDN asset or a GitHub Action, (4) running a fetched install script (`curl … | sh`). Do **not** re-fetch it for routine edits, reads, or running already-installed code. That's noise that burns tokens. Cache the result in `security.md` with the sweep date; reuse it within a session and refresh only if > 7 days old or one of the trigger actions recurs after the cached window.

### Supply-chain hardening

- **Pin exact versions, never floating ranges.** `==` (Python) + lockfile installs (`npm ci`, not `npm install`). A `>=`/`^` range auto-pulls whatever the registry serves next, the exact window a bad release lands in. Better still, hash-lock (`pip-compile --generate-hashes` + `--require-hashes`, `uv lock`, lockfile integrity hashes) to reject same-version re-publishes.
- **Subresource Integrity on every CDN asset.** `sha384` `integrity` on each `<link>`/`<script>`/import-map entry so a swapped file fails closed. Regenerate with `curl -sL <url> | openssl dgst -sha384 -binary | openssl base64 -A`; verify twice (a partial download yields a wrong hash that blanks the page). Self-host when feasible.
- **Pin CI actions to a full commit SHA + least privilege.** Every `uses:` pinned to a 40-char SHA (not a moving `@v3` tag) with a `# vX.Y.Z` comment, plus a minimal `permissions:` block per workflow. Re-pin with `gh api repos/<owner>/<repo>/commits/<tag> --jq .sha`.
- **Neutralize formula injection in exports.** Prefix CSV/TSV/spreadsheet cells starting with `= + - @`, tab, or CR with a `'`, or `=HYPERLINK(...)` runs when opened in Excel/Sheets.
- **No machine-local paths in committed data.** Store paths repo-relative; `/Users/<name>/...` leaks identity and layout into public history.
- **Every security fix ships with a regression test.** These regressions are invisible until exploited.

---

## Testing & validation

- **Write tests alongside code.** Every new module or bug fix includes them.
- **Regression-test every bug fix.** The bug is the test case; without one the fix rots.
- **Lock every displayed quote and citation to its evidence with a test.** Assert each quoted phrase appears *verbatim* in a stored evidence snippet, and that each citation link resolves to the exact location carrying the quote (when a precise locator is missing, e.g. FERC PDFs drop paragraph numbers from the text layer, anchor to the verifiable physical page instead). A future edit to a quote, or a reworded source, then fails loudly until re-verified, instead of silently drifting. This closes the gap a schema check can't see: well-formed text that no longer matches its source.
- **Don't claim text is "identical across all N" without checking every instance.** Template clauses, boilerplate, and multi-order statements look alike but differ subtly. A claim of "identical across all N" is provably false the moment one variant exists. Safe wording: "largely common, with per-instance tailoring." Safe test: check each quote against its own cited document — not just the canonical copy.
- **Stamp a page number on every quote surfaced from a multi-page document.** Locate the quote's start in the page-marked body text (`--- PAGE N ---`) and store the page it begins on. Render as `p. N` after the quote, linked to the filing. Guard with a test that recomputes every stored page so a stale or hand-edited number fails loudly; `null` when the start can't be located, never a guess.
- **Validate output against schemas before writing to disk** (Pydantic `extra="forbid"`, or zod).
- **Cover edges:** empty `[] / {} / ""`, null for every optional field, boundary values, combined filters.
- **Count-floor regression test.** For append-only datasets, assert total/item counts never drop versus the previous commit. Reintroduced caps and accidental deletions pass schema validation but fail a count floor.
- **Guard the whole garbage class, not the one bad row.** When a loose parser emits junk (a Table-of-Contents dotted-leader line harvested as a "finding"), don't just delete that row. Add a guard that scans committed output for the failure *signature*: dotted/ellipsis TOC leaders (`\.{6,}`, `…{2,}`), glyph artifacts (`(cid:NN)`), runaway field length, contentless titles. The signature catches the next variant before it ships. The cause is usually an unbounded greedy match (a final field that swallowed the rest of the document); bound the parse region and cap field length at the source.
- **Seed one example per enum value.** When the UI renders a legend/chips off an enum, test the dataset ships ≥ 1 record per value, so no legend slot renders empty and deleting the last example fails loudly.
- **Run the full suite before committing.**
- **Never ship test files to production.** CI excludes tests, fixtures, debug artifacts.
- **Tests are the eval suite**, the loop that tells you what works. Invest in it.

---

## Git discipline

- **Commit often** at natural checkpoints, small and focused: per module/feature, per bug fix (with its regression test), per doc update.
- **Messages explain *what* and *why***: "fix off-by-one in pagination when filter is empty," not "fix bug."
- **Never commit large binaries, downloaded data, or keys.**
- **Don't amend pushed commits**, and don't `--no-verify`. Fix the hook's underlying issue.
- **`git fetch` and integrate onto the latest remote before pushing to a shared branch.** Parallel agent / IDE / Codex sessions advance `main` mid-task; a stale base is rejected non-fast-forward. Check `git rev-list --left-right --count origin/main...HEAD`; if diverged with overlapping edits, re-apply onto the new structure rather than force-pushing (a force-push destroys the parallel work). At session start, `git branch -a` + `git log --all --oneline | head` to spot another tool mid-flight before assuming a clean starting point. Only clear a stale `.git/refs/.../*.lock` after confirming no `git` process is running.
- **Don't gate a commit on a piped filter.** `pytest … | grep passed && git commit` silently skips the commit when grep matches nothing (it exits non-zero). Run the tests, read the summary, then commit as a separate step.
- **No agent co-authors and no machine fingerprints.** No `Co-Authored-By:` for any AI tool, no "🤖 Generated with…" footers, no generic-assistant PR prose. Commits are owned by the human who ships them; write messages in their plain voice. Enforce with `git config --local claude.coauthor false` (set globally once to cover all repos).
- **Set commit identity deliberately.** Author with the account's noreply address, `git config --global user.email "<id>+<username>@users.noreply.github.com"`, and set `user.name "<username>"` too, or git falls back to the OS full name and leaks it. The human runs this; agents don't touch git config.

---

## Data handling

- **Append-only.** Append rather than overwrite; dedup by unique key.
- **Source attribution.** Every record carries its origin (source URL, connector, capture date) so any value traces back.
- **Defensive optional fields.** Null-check before rendering or processing.
- **Null renders as an explicit placeholder** ("N/A", "—"). Never a blank element.
- **Empty ≠ broken.** A legitimately empty result (clean audit, no matches) is valid. Render an explicit "none" state. An *extraction failure* is a bug. Log it and track coverage in `issues.md`. A silent `0` conflating the two reads as "covered everything" when it didn't.
- **Generated output commits with its source.** Seed + baked JSON, or rules + derived `llms.txt`, move together (a bisect must never land on an inconsistent state); assert the match with a test.
- **Capture dates over "current" framing.** Record `captured_at` and surface "as of YYYY-MM-DD"; record `archived_via` when a value came from a secondary/archived source.
- **Don't re-stamp `captured_at` on a re-parse.** A run that regenerates output from unchanged cached bytes preserves the original capture date. Load prior dates before processing and only re-stamp genuinely reissued (byte-different) sources. Stamping everything to today churns the audit trail and misrepresents provenance.
- **Keep bounded values, don't drop them.** A bare `\d+%` regex silently discards real rows like `>99%` / `<1%`; parse `[<>~]?(\d+)%`, keep the number, and carry the bound as metadata. Dropping unparseable-but-real values is a silent coverage gap, not a clean filter.
- **Preserve raw values when cleaning.** Normalizing a name/date/location/category? Keep the original in a parallel `*_raw` field. Cleaning is lossy, and raw is the only way to debug a bad transform or re-derive under new rules.
- **Cap by content, not count.** Trimming an append-only collection to a fixed count silently drops the oldest valid records. Bound by a content predicate (date window), store everything, limit *display* in the UI (top-N + "show all"). Log a threshold warning; never let the data layer enforce the cap.
- **Quality/confidence is its own field.** Keep geocoding confidence, match certainty, modeled-vs-observed separate from the value. A high-severity record with a low-confidence location differs from a clean one, and conflating them hides the gap.
- **Separate facts, estimates, and judgments** into distinct labeled lanes. A tool may have a view but mustn't manufacture certainty. Show the data and mechanism behind a recommendation, never a black-box score.
- **Publication date ≠ capture date.** Store the source's own publish date separately from `captured_at`; show publish when present, else capture. Don't fabricate a date for an undated source. Leave it null.
- **Absence of a judgment is meaningful.** An empty curator field (status, verdict) means "not yet assessed," not a default. Don't auto-fill or add a catch-all "unknown". Leave it off so the record reads as it did before the field existed.
- **Contested → show both sides.** When a third party documents a shortfall the subject disputes, tag it "contested" and surface both sources. Don't pick a winner. Reserve the strongest adverse status for ≥ 2 independent sources or a citable regulator/court finding.
- **Rates need denominators.** Raw counts mislead across groups of different size. Rank by a rate against an exposure measure (volume, population, length); label any raw-count ranking a triage heuristic, not a verdict.
- **Don't re-identify anonymized data.** Combined records can re-identify individuals. Aggregate small counts before surfacing; don't publish a precise individual narrative unless already public and necessary.
- **AI-synthesized values are provisional.** LLM aggregations from secondary round-ups aren't citation-grade. Audit each against a primary source, stamp `verified_at` + a per-row source; don't ship them as fact.
- **A 200 + a real file is not proof the source backs the claim.** A guessed identifier (docket / order / case number) can resolve to a real but *unrelated* document. Verify the *content* matches (page-1 caption: entity, date, identifier), not just that the URL loads. Prefer self-proving artifacts (a downloaded PDF with `page_count > 0`) over a metadata-only "verified" flag; the un-fetched escape hatch is the fabrication vector.
- **Gate an extraction against the source's own declared total.** Many documents state their own count ("Audit staff identified N areas of noncompliance"). Accept a parsed list only if its length equals N (or within a tight band like 90–100%); otherwise fall back to metadata-only rather than emit a partial or garbled parse as if it were complete. A self-declared count is a free oracle: use it to reject wrong verbatim text instead of shipping it.
- **Survey the real distribution before hardcoding an allowlist.** An exact-match allowlist drops the long tail (casing/prefix variants). Check the actual value distribution first, and filter on a stable underlying type, not the human-entered label, when one exists.
- **Prove a bulk deletion is content-free before trusting it.** When purging crawler junk or off-theme rows, regenerate the derived output and diff it: if `findings.csv` (or the equivalent product surface) is *byte-identical* after removing the rows, they carried no signal and the purge is safe. A changed output means you dropped real data. Stop and review. Crawler seeds silently accumulate off-theme noise (URL-encoded filenames, unknown type, 0 content, `structured=false`); audit by structural signature, not by eyeballing.
- **Enforce a source-host allowlist in code.** When data must come from authoritative origins, make the loader *raise* on any off-origin URL (e.g. non-`.gov`). Don't trust reviewer vigilance. Test it over every committed seed.

---

## Issue tracking (`issues.md`)

A living audit trail in the project root.

- Each bug: date, area, description, root cause (**code bug** vs. **test bug**), status (Open / Fixed).
- On resolution: the fix + the commit. Check whether a regression test is needed.

## Backlog (`backlog.md`)

- Add ideas immediately. Don't lose them. Each: description + priority (low / medium / high).
- Reprioritize periodically; demote stale "high" items rather than let them rot.

---

## Python standards *(when the project uses Python)*

- Type hints on all functions. `pathlib.Path` for paths. `logging`, not `print`, for runtime output.
- All constants in one config module. Pydantic for validation. Python 3.9+ unless specified.
- Pin dependencies with `==` (see Supply-chain hardening for hash-locking).

---

## Frontend standards *(when the project has a web frontend; full system in [DESIGN.md](DESIGN.md))*

- Functional components + hooks only. TypeScript strict, no `any`.
- Colors, enums, constants in a dedicated file, never inline.
- Data transforms in hooks/utils, not components.
- Loading, error, and empty states on every view. Visible focus indicators on every interactive element.
- **Mobile-first**; test at 375px before declaring done. **Touch targets ≥ 44px on touch** — apply the 44px floor under `@media (pointer: coarse)` so inline controls (tags, chips, "show more" toggles) keep their natural chip scale on desktop instead of bloating into CTAs next to lightweight elements.
- **Deduplicate image assets;** `<picture>` + `srcset` for AVIF/WebP/PNG. Never serve uncompressed PNGs for content. **Descriptive `alt`** on every content image.
- **Only load libraries used on the page.** No backend-only deps in read-only frontends.
- **Responsive CSS, not duplicate DOM trees.**
- **Budget the DOM.** Synchronously rendering thousands of nodes freezes the main thread (38k rows → ~265k nodes). Keep working sets in memory, render only a visible window (pagination + IntersectionObserver sentinel), hydrate in chunks across idle ticks, regression-test the node count. A sentinel can fire repeatedly before layout settles. Gate the append on a real scroll-distance check, not `isIntersecting` alone.
- **Lossy visuals keep the value in `aria-label`.** A glyph standing in for a number (checkmark for a count) carries the exact figure in `aria-label` so screen readers and tests still get it. Guard with a test.
- **The `[hidden]` trap.** A `display: ...` rule overrides the `hidden` attribute. Always ship a `[hidden] { display: none }` rule alongside it.
- **The ellipsis trap.** `overflow: hidden` + `text-overflow: ellipsis` silently no-op on a `display: inline` element (a bare `<span>`). Set `block`/`inline-block`/`flex`/`grid` on anything you expect to ellipsis, plus `min-width: 0` on a flex/grid parent so the column can shrink below intrinsic width.
- **Lazy-load heavy CDN libs; never block `<head>` on them.** A blocking `<script>` for a large lib (pdf renderer, charting engine) adds full-load latency and makes test suites flaky (`page.goto(..., "load")` waits on CDN). Load async on first user action (`await import(...)` or a thin wrapper). Store the SRI hash in a constant so it's auditable; don't skip SRI just because it's lazy-loaded.
- **Footer carries attribution + source.** Every shipped site footer credits the author and links the code: include `pranavaraparla.com` and the project's GitHub repo. One line, understated.
- **Don't ship the "AI-generated dashboard" look.** Generated UIs have tells that read as untrustworthy templated filler — strip them: (1) **eyebrow kickers** (tiny uppercase colored labels above every heading); (2) **cutesy section names** ("The receipts", "In their words", "Where it goes") — use plain, journalistic titles; (3) **stat cards with a colored left accent stripe + drop shadow** — prefer flat, hairline-bordered tiles; (4) **badge pills** for status (a green rounded chip with a circle checkmark) — use one understated line of text; (5) **gratuitous hover-lift** (`translateY` bounce) on every card; (6) **gradient/glass everything**. Lean flat and editorial: real type hierarchy, borders over shadows, restrained color (reserve hue for data, not chrome), self-hosted fonts. Litmus test: if it looks like every other LLM-built landing page, redesign it to look like a tool a newsroom or a product team shipped.

---

## Performance, reliability & bandwidth: measure, don't guess

Ship targets, then track them against real users; Google ranks on p75 *field* data, not lab averages.

- **Core Web Vitals at p75, segmented by page/device/percentile.** The `web-vitals` library reports LCP/INP/CLS for free; beacon batched on `visibilitychange`, sample at high traffic. Synthetic (Lighthouse CI) catches regressions pre-merge, RUM catches what real devices see. Run both.
- **Budget page weight + request count, fail CI on regression.** A `size-limit`/bundlesize check per route so a heavy dep fails loud, not silent. Benchmark against the lightest site in the portfolio.
- **Track bandwidth over time.** A 3× jump in transfer size / request count is a regression to investigate. (The reducing levers (AVIF/WebP, tree-shake, code-split) live in Frontend standards; this is about *watching the number*.)
- **Track error rate + uptime.** Beacon client errors (`window.onerror` or the analytics tool). A spike after a deploy is the roll-back signal. Backends also track request error rate + p95 latency.
- **Put before/after weight + CWV in any hot-path PR.** A number beats "feels fast."

### Website analytics: privacy-first, not GA4

For a content/static site, default to a **cookieless, privacy-first** tool (no consent banner, <2 ms script):

- **Skip GA4 by default:** ~2.5 MB + ~17 ms, cookies/fingerprinting, GDPR-non-compliant in parts of the EU, and consent fatigue drops 40–60% of EU traffic from the data. Use it only when you need its ad-attribution/funnels and accept the weight + banner.
- **Decision rule:** on Cloudflare → **Cloudflare Web Analytics** (free, barebones, samples). Want portability/self-host → **Plausible** (~1 KB, EU-hosted; Umami/Fathom equivalent). On Vercel and staying → **Vercel Web Analytics** (zero-config but lock-in, never the reason to stay). Need deep attribution → GA4. Never proxy a tracker through your own domain to dodge blockers (Security → privacy).

---

## Network ethics & rate limiting *(when fetching from external sources)*

- ≥ 1.5–2s between requests to one host. Informative `User-Agent`. 429 → exponential backoff from 10s.
- Cache all fetched content to disk; re-runs never re-download.
- Persistent block after retries → log to `issues.md` and skip, never crash.
- **Start small:** validate against a handful of pages before a full run.

---

## AI / API cost optimization *(when the project uses LLM APIs)*

- **Don't spend tokens on deterministic work: use a library, not an LLM.** Extracting text from a text-layer PDF, parsing a structured file, reshaping data: a library (PyMuPDF/`fitz`, a real parser) does it reproducibly. One full-text-via-agents extraction hit the session limit and burned ~974K tokens for *zero* output; the PyMuPDF redo did the identical job in ~2s for 0 tokens. Spend tokens only on judgement (classify, summarize, decide); never on transcription a tool does exactly and for free. Anything that must round-trip verbatim is a library job, not an agent job.
- **Decompose document/comment analysis into auditable subtasks; the quote is the atomic unit.** Don't one-shot a summary over a corpus: **chunk → extract verbatim quotes → bin against a controlled vocabulary → synthesize each bin from its quotes.** Store prompt + input + output per item so every tag traces to a source span. Run a cheap deterministic keyword pass first as prior and cross-check — LLM extraction runs ~80% precision / ~20% recall, so never ship unaudited. Fold self-critique into the extractor (body already in context, ~8K) rather than a separate audit agent (~35K). Add deterministic checks (verbatim-quote test, controlled-vocab check, style/boilerplate linter for AI-register words and em-dashes) until the LLM audit only judges what code can't. Spawn an independent skeptic only on deterministically flagged items (lens-divergence from keyword prior, zero/thin quotes, all-neutral stance) — ~15–25%, not all. Measured: a blanket per-item audit was ~45% of tokens for a 1-in-6 catch rate.
- Cheapest model that meets quality (Haiku before Opus). Keyword pre-filter before expensive calls. Truncate/excerpt input.
- Cache responses by content hash; never re-classify identical content.
- Log cost per layer; print a run summary. `--dry-run` and `--fetch-only` work without an API key.

---

## Working with AI agents (meta-principles)

- **Research is triggered by a specific gap, not by default.** Resolution ladder for any coding question: grep the repo → read the relevant file → one targeted web fetch → ask the user. Don't run multi-source research sweeps for tasks answerable from the codebase. A full web-research pass costs 20–50K tokens; most code tasks cost under 5K. Fetching more than 2–3 URLs for a single coding task is a signal to stop and ask instead.
- **A faster/cheaper agent run usually *failed*.** A deep-research or workflow fan-out that finishes quicker and cheaper than expected has often died mid-way and returned nothing. Confirm the result object is non-empty before trusting the metric. And reserve fan-outs for genuinely open-ended questions: one deep-research pass is tens of subagents and millions of tokens. If you can enumerate the sub-questions yourself, do the work inline (grep → read → one fetch).
- **Context is RAM, not memory.** (Karpathy: LLMs are "fuzzy CPUs.") Fill it with what the task needs, no more. Watch for context poisoning (compounding early errors), distraction (noise burying signal), and clash (contradictory instructions).
- **Early expensive operations compound.** Every tool result is re-fed on every later turn, so a costly turn-2 mistake multiplies all session. Keep early turns cheap, defer heavy work, `/clear` rather than carry bloat. Suppress verbose output by default (pipe to `tail`; read full only on failure). A re-run re-injects the whole thing.
- **Inline before subagent.** A subagent costs ~25–40K tokens of orchestration; an inline `WebSearch` ~5–10K, a `grep` near-free. Spawn only for synthesis, adversarial verification, or 10+-file exploration; do routine "find X" / "understand this module" inline. In a fan-out the verify phase is the cost sink (~80% of subagents, cache tokens dominate). Lower the verify-claim cap, one vote per well-sourced fact.
- **Start fresh on topic switches.** `/clear` between unrelated problems; break complex tasks into small committed steps.
- **AI has no taste.** Review output for: excess try/catch, needless abstractions, bloat instead of refactoring, generic naming (`data`, `result`, `utils2`), comments that restate code, gratuitous emoji or marketing tone. The fix is one thing: **match the surrounding code's idiom** so a diff doesn't announce a different author.
- **AI-sounding prose is a tell too.** Scrutinize shipped words (UI copy, empty states, READMEs, generated narrative) as hard as code. Cut the LLM register (*delve, leverage, robust, seamless,* "it's worth noting"), marketing vapor, rule-of-three padding, hollow summaries. Lead with the specific; short declaratives; read it aloud. Full list in [DESIGN.md § 11.1](DESIGN.md). On drafting: if a paragraph fights back, source more, don't draft more; the struggle means you don't understand the topic yet. Confident first draft, light edit, shelve a weak one rather than sand it down.
- **The four agent failure modes** (Karpathy), each already a rule here: (1) unverified assumptions → surface tradeoffs, ask first; (2) abstraction hypertrophy → minimum code; (3) collateral changes → touch only what the task needs, log adjacent cleanup in `backlog.md`; (4) no success criteria → define "done" and loop until verified.
- **AI is a tool, not a substitute for discipline.** Apply the fundamentals (perf audits, bundle analysis, review) to generated code. High LOC means nothing if it's bloated.
- **Vibe coding for throwaway; engineer the rest.** The moment a user depends on it, you owe it *agentic engineering* (vibe coding raises the floor; this raises the ceiling). Litmus test: **can you defend the output** under review? If not, you're still vibe coding.
- **Intent specification is the new coding.** The unit shifts from typing lines to delegating macro-actions; the scarce skill is judgment: what to delegate, how to specify, how to review fast. Write non-trivial logic as a prose spec first (trigger, inputs, mechanism, success criteria). **LLMs automate what you can verify**: build the feedback loop first.
- **Make instructions agent-legible.** Setup/deploy/run steps as copy-pasteable markdown blocks, not brittle scripts. Document the APIs, CLIs, and logs an agent can sense and drive. The more it can sense and drive, the more it closes the loop unattended.
- **Closed-loop validation** is the biggest force multiplier: when the agent can answer "did it work?" itself, every iteration is fast.
- **Keep this file current.** Append concise notes when something surprises you (a failed pattern, a correct invocation, a quirk). This is scar tissue. Grow it, don't rewrite it.
- **Write big plans to files.** Spec large tasks to a `docs/` markdown file and review before executing.
- **Sweep for orphaned wrapper shells after long-running commands.** A background polling wrapper (`until ps -p $(pgrep -f "...")...; do sleep N; done`) can outlive its process: once the PID exits, `pgrep` returns empty and the `until` loop never resolves, sleeping forever. Run `pgrep -fl "<project-path>"` before declaring done and `kill` stragglers. Fixes: prefer a Monitor tool over inline polling, or invert to `while pgrep -f "..."; do sleep N; done` so the loop exits when the process disappears.

---

## Influences

- **Andrej Karpathy**: "make it work, then make it good"; LLM-as-fuzzy-CPU; eval-as-the-loop ("LLMs automate what you can verify"); context over prompt engineering; the closed-loop bar for trustworthy agents; the 2026 shift from vibe coding to *agentic engineering* (intent spec + task decomposition) and the four failure modes (unverified assumptions, abstraction hypertrophy, collateral changes, missing success criteria).
- **Pieter Levels (levels.io)**: ship fast and ugly; boring tech beats shiny; solo-friendly defaults (vanilla, SQLite, single-file, cheap hosting); profit before scale; don't add a dependency you can't maintain alone; talk to users daily.

When in doubt: **ship the smallest version that works, then iterate on what real users do, not what you imagine they'll do.**
