# DESIGN.md: Universal Visual & UX Principles

> Base file for every project in this folder with a UI. Project-specific `design.md` files extend this with palette, motif, and content rules. When project conflicts with base, project wins.
>
> Companion files: [CLAUDE.md](CLAUDE.md) is the engineering principles; [AGENTS.md](AGENTS.md) is the agent workflow.

---

## 1. Posture

Three principles set every call below:

1. **Refuse the default look (top priority).** Shipping the generic AI aesthetic (violet-to-indigo gradient, centered hero with a gradient headline and two buttons, the same sans everywhere, emoji feature cards on slate-gray) reads instantly as "a model made this" and makes the product interchangeable with a thousand others. A real product looks *decided*: each one earns a specific, defensible identity anchored in its subject. See §1.1; this overrides convenience every time.
2. **The content is the product. Chrome earns its pixels.** Anything that isn't the primary surface (map, feed, list, form, canvas) justifies itself by helping the user understand or narrow it. Backgrounds, textures, and decoration sit low (≤~10% opacity/contrast) so anything assertive is real data. Every color encodes meaning; decorative color competes with the data for attention.
3. **Performance is a design constraint, not a follow-up.** Every "nice touch" (web font, blur, full-page animation) competes with first paint and the 60fps budget. Choose perf when they conflict.

Aesthetic follows the product: an editorial dashboard reads like the FT; a consumer app like its category; a government tool like a public record. Don't paste one voice onto another. Project `design.md` carries the *specific* identity; this file carries the *universal* rules it must respect.

### 1.1 The default-AI tells, and what to do instead

The giveaways of an unconsidered, model-generated UI. Each right-hand cell is the *minimum* move away. This isn't optional polish. It's what separates a product from a demo.

| Default-AI tell | Do instead |
| --------------- | ---------- |
| Violet→indigo (or teal→blue) gradient backdrop; gradient-filled headline text | Commit to a flat palette **derived from the subject** (a water tracker → deep-water blues; a crash atlas → newsprint black/white with one alarm red; a finance tool → ledger greens on cream). One accent, used sparingly. Gradients only when they encode data (a scale, a ramp). |
| The same neutral sans (Inter / Geist / Roboto) on everything | Pick a pairing **with a point of view**: a real display face (serif, slab, or a distinctive grotesque) against a quiet workhorse. System stacks are still the default for perf (§2), but *choose* the stack deliberately; don't accept the first one. |
| Centered hero: big headline + subtitle + two buttons, nothing below the fold but feature cards | **Lead with the tool or the content.** The first screen should *do* something: show the map, the table, the feed, real numbers. Asymmetric and editorial layouts beat the symmetric marketing-page template. |
| Three-up grid of cards, each with an emoji icon and a sentence | Break the grid. Use scale, density, and rule lines to build hierarchy. Real iconography or none. Emoji is not an icon system (§11). |
| Glassmorphism, `backdrop-blur`, and a soft drop shadow on every surface | Choose **one** structural device (hairline rule lines, a hard border, a visible grid) and commit to it. Flat surfaces read as more serious and cost less per frame (§10). |
| Everything rounded to the same `1rem`/`2xl` radius | Vary radius with meaning (§5). Sharper corners read as editorial/authoritative; soft corners as friendly/consumer. Pick per project, don't default. |
| Dark mode = slate `#0f172a` with indigo accents | Derive the dark surface from the project's own palette, not the framework default. |
| "✨ New", "Beta" pill ceremony; vague benefit-copy ("Powerful insights at your fingertips") | Concrete labels, real counts, source trails. Say what the thing *is*, with a number. |

**Get creative on purpose:** before writing CSS, name the identity in one line in the project `design.md`: a reference point (a publication, era, or object), a subject-anchored palette, a type pairing, and **one memorable move** that's yours (a masthead rule, textured paper ground, monospace data spine, hand-tuned chart style). One deliberate move escapes the default; the rest of this document keeps it disciplined.

---

## 2. Typography: system stacks only by default

No web fonts unless justified: a Google Fonts link costs a render-blocking RTT and ~50KB, and the system stack approximates Charter / Inter / SF Mono everywhere.

```css
--font-sans:  -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui,
              "Helvetica Neue", Arial, sans-serif;
--font-serif: "Charter", "Source Serif 4", "Source Serif Pro",
              "Iowan Old Style", "Apple Garamond", "Palatino", "Georgia",
              "Times New Roman", serif;
--font-mono:  ui-monospace, "SF Mono", "JetBrains Mono", Menlo,
              Consolas, monospace;
```

- **Serif for editorial display** (H1, hero H2, KPI numerals, verbatim quotes). Signals "this is content, not chrome."
- **Sans for body and UI** (everything else).
- **Mono for code, IDs, paths, share codes.** Anything that has to round-trip a copy/paste.
- **Tabular numerals.** `font-feature-settings: "tnum"` on `:root`. Any column of numbers (KPIs, table cells, dates, counts) lines up.

If the project genuinely needs a custom font (rare, most don't), audit the alternative system stack on target browsers before introducing a fetch.

---

## 3. Color tokens

**All colors live as CSS custom properties on `:root`, with `[data-theme="dark"]` overrides.** JS reads via `getComputedStyle()`. Never hardcode a hex outside `:root`.

```css
:root {
  --bg: …;          /* page background */
  --surface: …;     /* cards, panels */
  --surface-2: …;   /* inputs, secondary surfaces */
  --border: …;
  --text: …;
  --text-muted: …;
  --accent: …;      /* primary CTA, focus ring */
}

[data-theme="dark"] {
  --bg: …;
  /* ... */
}
```

### 3.1 Semantic separation

When a project uses color to encode meaning (status, stance, category), keep *meaning* and *brand* in separate token families:

- **Brand / surface tokens**: neutral chrome (`--bg`, `--surface`, `--text`).
- **Semantic tokens**: meaning (`--status-{success,warning,error}`, `--stance-{positive,mixed,negative}`).
- **Category tokens**: distinguish without ranking (`--category-{a,b,c}`).

Never conflate them. Coloring "category" with the same palette as "status" tells the user "category A is bad," which is rarely what you mean.

### 3.2 Brand-adjacent colors are not brand colors

When showing third-party brands (companies, products, services), use **brand-adjacent but neutral** tones: desaturated versions that distinguish without implying endorsement. Using a company's actual brand color implies affiliation and invites legal questions.

### 3.3 Theme swap is JS, not filter

Toggle light/dark via the CSS variable swap plus a JS pass over any canvas/SVG layers reading the variables. Never `filter: brightness/contrast` a tile pane or content layer. It recomposites every frame and tanks mobile perf.

---

## 4. Spacing scale

A 4 / 8 px ladder covers ~99% of cases:

`4, 6, 8, 10, 12, 14, 16, 18, 22, 24, 28, 32`

Round `7px`/`13px` to the nearest step unless you have a reason. Skip an explicit `--space-2` variable until a refactor would save more LOC than it churns.

---

## 5. Radii, shadows, motion

- **Radii:** `4` (chips), `6` (small inputs), `8` (buttons, cards), `12` (modals), `14` (mobile bottom sheets), `999` (pills).
- **Shadows:** one soft (`0 1px 2px rgba(0,0,0,0.06)`) for at-rest cards; one elevated (`0 4px 18px rgba(0,0,0,0.08)`) for panels and toasts. Dark theme uses heavier alpha (`0.4–0.5`) because contrast against a dark `--bg` needs more.
- **Motion:**
  - `90ms`: table row hover, color swaps
  - `120ms`: button / input hover
  - `200ms`: panel slide-in/out, modal open
  - `300ms max`: toast, fade
  - **No motion above 300ms.** No CSS animations on hot paths (pan / zoom / scroll).
- **Respect `prefers-reduced-motion`.** When set, kill panel transforms and any non-essential transition.

---

## 6. Layout: mobile-first, three breakpoints

Default to three viewport bands, matched 1:1 with Tailwind defaults:

| Width band     | Name    | Tailwind prefix | Layout shape                                     |
| -------------- | ------- | --------------- | ------------------------------------------------ |
| `< 640px`      | Mobile  | (none)          | Single column, sticky toolbar, FAB, bottom sheets |
| `640–1023px`   | Tablet  | `sm:`, `md:`    | 2-up grids, full CTA labels, hamburger nav        |
| `≥ 1024px`     | Desktop | `lg:`           | 3-up / 4-up grids, inline nav, side panels        |

A fourth tier is rarely justified. Desktop scales fine above 1280 if you cap content width (`max-width: 1280px; margin: 0 auto`).

**Don't use container queries unless an independent embedded component needs them.** Viewport media queries are simpler, work everywhere, and match how the rest of the layout reasons.

**Don't duplicate DOM trees for mobile / desktop.** A `<section class="hero-copy">` that's `display: none` on mobile is fine; rendering a separate mobile-only block is not.

---

## 7. Mobile patterns

- **Bottom sheets, not full-page overlays**, for detail panels and filters. A full overlay covers the primary surface and breaks the "tap a result → read → keep browsing" loop.
- **Carousels (scroll-snap), not stacked grids**, for KPI strips. Stacking pushes the primary surface below the fold.
- **Hide hero copy on mobile**, keep KPI / summary chips. The user already knows what they opened.
- **Bump input font-size to 16px on iOS** to suppress auto-zoom on focus.
- **Respect safe-area-inset.** Bottom-edge FABs, sheets, and bars use `bottom: max(1rem, env(safe-area-inset-bottom))` so they don't sit under the home indicator.
- **Sticky toolbars** so users can switch views from any scroll position; keep them slim (~52px).
- **Touch targets ≥ 44 × 44px.** Non-negotiable. Even for "small" admin actions.
- **The `<details>` primitive is preferred over JS accordions.** Native, keyboard-accessible, screen-reader-friendly; `open` toggle doesn't re-render the inner content.

---

## 8. Components

### 8.1 Buttons

| Variant   | Use                                  | Spec                                                 |
| --------- | ------------------------------------ | ---------------------------------------------------- |
| Primary   | The one CTA per view                 | Filled `--accent`, white text, rounded 8/12          |
| Secondary | Adjacent actions                     | Bordered, transparent bg, accent text                |
| Ghost     | Tertiary / inline                    | No border, no bg, accent text, hover bg `--surface-2` |
| Icon      | Toolbar (filters, theme, share)      | 32×32 (44×44 touch target), rounded 8, hover bg     |

Focus state is a 2px `--accent` outline with 2px offset via `:focus-visible` (not `:focus`) so mouse users don't see it on click.

### 8.2 Pills

A single base `.pill { padding: 1px 8px; border-radius: 999px; font-size: 10.5px; font-weight: 600 }` with semantic variants. Outline pills (`.pill.outline`) for "candidate" / "eligible" / "ready" signals; solid pills for status. Stack left-to-right as a readability ladder (program → status → readiness).

### 8.3 Cards

`background: var(--surface); border: 1px solid var(--border); border-radius: 12; padding: 16` is the safe default. Use shadow `0 1px 3px rgba(0,0,0,0.05)` at rest, `0 4px 12px rgba(accent, 0.15)` on hover.

### 8.4 KV grids (detail panels)

```html
<dl class="kv">
  <dt>Label</dt>
  <dd>Value <span class="dd-note">optional sub-line</span></dd>
</dl>
```

`grid-template-columns: 130px 1fr` on desktop, `110px 1fr` on mobile. Null values render as italic muted (`<dd class="muted-cell">Not available</dd>`), never blank.

### 8.5 Toasts

One at a time. Don't grow into a queue. If you need stacked toasts, swap in a real library. Lazy-mount a single `#toast` div, fade in via `.visible`, auto-fade after 4s.

### 8.6 Comparison matrix

A matrix answers a binary question: "does this entity touch this dimension at all?" Render a single `✓` per populated cell, not a count. Volume belongs in the subsidiary list, not the at-a-glance grid; digits make the matrix harder to scan and over-state precision.

---

## 9. Accessibility (baseline)

| Concern                | Implementation                                                                |
| ---------------------- | ----------------------------------------------------------------------------- |
| Skip to content        | `<a class="skip-link">` is the first focusable element; visually hidden until focused |
| Landmarks              | `<header role="banner">` · `<nav>` · `<main role="main">` · `<aside>` · `<footer role="contentinfo">` |
| Focus indicators       | `:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px }` on every interactive element |
| Clickable non-buttons  | A table row / card / `div` used as a control gets `role="button"` + `tabindex="0"` + an Enter/Space key handler + a focus-visible ring. A bare `onclick` is mouse-only: invisible to keyboard and screen readers |
| Live region for counts | `<span aria-live="polite">` so result counts and dynamic state changes announce |
| Filters as fieldsets   | `<fieldset><legend>` for grouped controls                                     |
| Tabs                   | `role="tablist"` / `role="tab"` / `role="tabpanel"` / `aria-controls` / `aria-selected` |
| Color contrast         | All text/bg pairs ≥ 4.5:1 in both light and dark themes (verify with audit tools) |
| Reduced motion         | `@media (prefers-reduced-motion: reduce)` kills non-essential transforms      |
| Touch                  | `touch-action: manipulation` on interactive elements                          |

---

## 10. Performance constraints on design

Design decisions that look like aesthetic calls but are actually performance calls:

| Choice                                      | Reason                                                      |
| ------------------------------------------- | ----------------------------------------------------------- |
| System fonts only (default)                 | Save a render-blocking RTT + ~50KB                          |
| No `backdrop-filter: blur` on map / overlay | Recomposites on every pan/zoom frame                        |
| No `filter:` on hot panes                   | Same                                                        |
| CSS-var theme + JS re-paint                 | Theme swap doesn't trigger a full re-style cascade          |
| Canvas markers, not SVG                     | SVG nodes melt mobile at 10k+                               |
| Pagination + IntersectionObserver           | DOM stays small; sentinel auto-appends only when needed     |
| Lazy-load non-default data layers           | First paint stays small                                     |
| Lazy-load a blocking third-party `<script>` (cdnjs html2pdf, etc.) from the handler that needs it, not `<head>` | A render-blocking `<script>` in `<head>` delays first paint *and* stalls every Playwright `page.goto`: one e2e suite went from ~11 min with 5–13 flaky load timeouts to ~52s / 0 failures once it was deferred. Keep SRI on the lazy import |
| `<link rel="preload">` for critical JSON    | Races the JSON behind defer-loaded JS                       |
| `priority: "low"` on enrichment fetches     | Browser deprioritizes behind first-paint resources          |
| `contain: layout paint` on heavy panels     | Bounds invalidation cost when content re-renders            |
| Pre-render to static HTML, not a client runtime | A client-side WASM runtime cold-starts in tens of seconds; the same site pre-rendered to static HTML paints near-instantly |

If a proposal trades any of these for visual polish, it either (a) proves it works on a mid-range Android over throttled connection, or (b) gets explicit sign-off that the perf cost is acceptable.

---

## 11. Editorial / content rules

These apply to any project that surfaces data, claims, or content from external sources.

- **Cite primary sources.** Every numeric claim links to a primary/authoritative source, or it doesn't ship.
- **Source lines are bylines, not hidden metadata.** Every chart, KPI, and table carries its agency + capture date + link, compact but visible, a footnote, not a tooltip the reader has to hunt for.
- **A citation chip names the destination it links to, not a loose association.** If a source chip links to POWER Magazine, label it "POWER Magazine", not the author's primary affiliation ("Duke"). The link target and the visible credit must agree, or the chip misattributes. Keep the person + affiliation on the card; keep the publisher on the chip that opens it.
- **Separate fact from estimate from judgment.** Render observed facts, modeled estimates, and policy/editorial judgments as visibly distinct tiers; never let a confident-sounding estimate read as a measured fact. A composite score (safety index, risk rank) always shows its components, no black-box number.
- **Mechanism-first policy language.** "Shorten the crossing distance," not "make it safer." Name the lever, not the vibe.
- **Frame vocabulary forward, not deficit.** Load-bearing product terms set the user's mental model. *Top need* and *upgrade opportunity* point forward where *weakness* points back. Choose the framing in the project `design.md`, mirror it in field names and labels, and enforce it with a test that greps the build for banned words.
- **Surface "why".** Boolean badges ("Eligible", "Verified") carry their qualifying criteria inline (italic sub-line or tooltip). The badge alone is opaque.
- **One surface, two audiences: lead lay, demote expert, keep the load-bearing number in the open.** When a page serves both a layperson and a specialist (patient + clinician, citizen + analyst), open with the plain-language answer and tuck the expert detail behind `<details>`, but never bury the one fact both audiences need (the drug strength, the dollar figure, the deadline). Progressive disclosure hides depth, not the answer.
- **Title-case CAPS source data at ingest.** Government/scraped feeds ship ALL CAPS or sentinels (`-- Not Defined --`, `_NULL_`). Run `prettyName()` at ingest, preserve raw on `*_raw`, and keep an acronym whitelist (NASA, NPS, USA, …).
- **"Not available", not blank.** Optional fields render as italic muted placeholders.
- **"Adjacent", not "0.0 mi".** Render `n < threshold` as a meaningful word, not a misleading number.
- **No emojis by default.** Outline pills do the badge work. If the project's voice needs emoji (consumer/social), use sparingly and document in `design.md`.
- **Lowercase prose, uppercase labels.** Eyebrows, KPI labels, table heads, outline-pill text are uppercase with `0.04–0.14em` tracking; everything else sentence case.
- **AI-generated content is visibly distinguished**: a 3px accent left-border plus a model-credit meta line. The reader should never confuse primary data with generated narrative.
- **Borrow design *values*, never imitate a brand.** Take the useful values from a reference publication (high-contrast type, disciplined grids, rule lines, source trails, calm authority), not its masthead, logo, proprietary fonts, or furniture that implies you *are* them. The first screen is the tool, not a marketing page.

### 11.1 Voice: write like a person, not a model

Every word that ships (headings, labels, microcopy, empty states, tooltips, generated narrative, user-facing READMEs) gets a plain, specific voice. The model register is as recognizable in copy as the violet gradient is in layout (§ 1.1). This is the prose half of "refuse the default look."

**Tells to cut:**

| Tell | Example |
| ---- | ------- |
| LLM register words | *delve, leverage, robust, seamless, elevate, unlock, empower, harness, tapestry, testament, underscore, pivotal, crucial, comprehensive, cutting-edge, game-changer, ever-evolving, realm, navigate the complexities of* |
| Filler & throat-clearing | "it's worth noting that", "it's important to note", "in today's fast-paced world", "when it comes to", "at the end of the day" |
| Marketing vapor | "powerful insights at your fingertips", "take your X to the next level", "the ultimate solution for", "designed to help you" |
| Mechanical rhythm | rule-of-three everywhere ("fast, simple, and powerful"); "not only… but also"; the "X, not Y" antithesis as a headline mannerism ("Tailored, not uniform"; "a feature, not a hedge"), rewrite to a plain declarative; every sentence the same length |
| Hollow summaries | "In conclusion", "Overall", a closing line that restates the opening |
| Hedging when you know the answer | "generally", "typically", "in most cases" used to soften a fact you're sure of |
| Ceremony | emoji in body copy (per § 11), em-dash padding, exclamation marks selling a feature |

**Do instead:**

- **Lead with the specific.** A number, a name, a date beats an adjective: "Tracks 49 cases since 2014," not "comprehensive tracking of enforcement actions."
- **Short declaratives.** Say the thing and stop. Vary sentence length because a person would, not for rhythm.
- **Concrete verbs, plain nouns.** "Download the report," not "seamlessly access your documents."
- **Cut the warm-up.** If the first sentence only clears its throat, delete it and open on the point.
- **Read it aloud.** If you wouldn't say it to a colleague, rewrite it.
- **No em-dashes in displayed prose** (house style across these projects). The em-dash reads as a model tic at scale; replace it with a comma, colon, period, or parentheses as the sentence needs. Verbatim quotes, reporter cites, and source titles are exempt. Range dashes become "to" when the identifiers already contain hyphens ("EL26-67-000 to EL26-72-000", a dash there is ambiguous). Enforce with a grep test over the rendered build.

The test mirrors the code rule ([CLAUDE.md](CLAUDE.md) → "AI has no taste"): *would a careful human writer have written this line?* If it reads like it was generated to fill space, cut it or rewrite it.

### 11.2 SEO & social metadata

For any public page, get the share card and the dates right. They're how Google, LLMs, and social scrapers read the page:

- **Social-card OG images: ship JPG, not WebP.** LinkedIn (and some other scrapers) won't render WebP link previews. Use a JPG hero for `og:image` / `twitter:image` (`summary_large_image`); fall back to a default image for pages without a hero.
- **`datePublished` ≠ "last updated."** Derive each page's `datePublished` from its first commit (clamp to ≤ `dateModified`) and omit it when unknown; use the content's refresh date only for `dateModified`. Feeding the "last updated" value into `datePublished` republishes old pages on every data refresh, misleading to Google and LLM consumers.
- **Sitemap `<lastmod>` is the real per-page change date, never today's stamp.** And a no-op QA/UAT or "zero regressions" commit is not a content update. Date-bump logic that feeds ordering, `lastmod`, or a displayed "updated" date must skip routine non-content commits and keep the last *meaningful* change date.

---

## 12. Common pitfalls (the "scar tissue" list)

These are encoded across this folder's projects. If you're tempted to undo them, read the rationale.

### 12.1 The `[hidden]` trap

`display: inline-flex | block | flex` on an element that uses the `hidden` HTML attribute silently overrides the implicit `display: none`. The element renders despite `hidden` being set.

**Always** ship a `[hidden] { display: none }` rule alongside any `display: ...` override. If the element animates out (e.g. slide), use `visibility: hidden` + `transform` on `[hidden]` instead.

### 12.2 `text-overflow: ellipsis` no-ops on `display: inline`

A `<span>` defaults to `display: inline`; `overflow: hidden` + `text-overflow: ellipsis` silently does nothing. Always set `display: block | inline-block | flex | grid` on the element you're ellipsizing. Pair with `min-width: 0` on the parent grid item.

### 12.3 IntersectionObserver callbacks need a scroll-position guard

`isIntersecting === true` is necessary but not sufficient for "user scrolled near the bottom." During tab swaps and in headless contexts, layout can settle in multiple paint passes, firing the observer several times. Each firing prefetches another page. Add an explicit `scrollHeight - scrollTop - clientHeight > 400` check to bail when the user hasn't actually scrolled.

### 12.4 Anything that enumerates a fixed list MUST iterate the source-of-truth array

Reset buttons, dropdown populators, persona buttons, anything that touches "all programs / themes / tiers / categories" must iterate from the canonical constant array, never a hardcoded subset. When the list grows, the iterating code picks up the change for free; the hardcoded subset silently drops the new entries.

### 12.5 No web fonts without sign-off (see § 2)

### 12.6 No CSS `filter` on hot paths (see § 10)

### 12.7 Pills do NOT fall back across columns

When a row has a "Program" column and a "Status" column, the Status cell must render Status-specific content (or `—`), never the Program pill as a fallback. Two identical pills doubles visual noise without adding signal.

### 12.8 The default-AI aesthetic (see § 1.1)

Violet/indigo gradient + centered hero + two buttons + same sans + emoji cards = the model default, and it reads as disposable. Anchor a real identity in the subject first (§ 1.1). Highest-priority visual rule here, not a nice-to-have.

### 12.9 Fetch from absolute paths, and check `response.ok`

Fetch data from absolute paths (`/data/x.json`), never relative (`../data/x.json`). Relative paths break silently when the page's directory depth changes. And `fetch(...).then(r => r.json())` swallows a 404/500 into a confusing parse failure: throw on `!response.ok` with the status, and render the actual `error.message` (not a generic "failed to load") so debugging isn't blind.

### 12.10 Cache-bust user-facing assets, and rule out stale cache first when debugging

A browser serving an old `app.js` is the most common silent frontend failure. The error you see is from code that no longer exists. Version JS/CSS (`?v=YYYYMMDD`) so deploys bust the cache, and when debugging a frontend bug, hard-refresh as step one before touching code.

### 12.11 Mobile collapse must be deterministic

Don't drive a responsive show/hide off the `hidden` attribute or a native `<details open>` default alone. Once restyled, their behavior is inconsistent across breakpoints. Drive open/closed from a `matchMedia` listener with an explicit `display: none` per breakpoint (collapsed on mobile, forced visible on desktop), so the state never rides on attribute quirks. (`<details>` is still the right primitive for *user-toggled* disclosure per § 7. This is about *breakpoint-driven* collapse.)

### 12.12 A `var()` alias resolved in `:root` doesn't inherit the dark-theme override

Aliasing a semantic token to a base token in `:root` only (`--tariff-accent: var(--stance-positive)`) does **not** pick up the `[data-theme="dark"]` override. The alias resolves once against `:root`, so descendants in dark mode keep the light value and badges/chips/icons render wrong. Define the token with **literal values in both** `:root` and `[data-theme="dark"]` (mirror the working `--stance-*` / `--status-*` families); don't alias across token families and expect the theme cascade to follow.

### 12.13 `#page=N` only jumps on a same-origin, inline-rendered PDF

A deep link to a PDF page (`href=".../order.pdf#page=60"`) lands on the page *only* when the browser renders the PDF inline from the same origin. A cross-origin PDF, or one behind Cloudflare or an attachment `Content-Disposition`, ignores the fragment (or downloads instead). To deep-link a page, commit/serve the PDF same-origin; keep the official external URL as a separate visible link. Regression-test that each link's target page actually contains its quoted text.

---

## 13. What's intentionally NOT in design

Decisions made by *omission*:

- **No icon libraries by default.** System glyphs + outline pills cover most needs. Add Lucide/Heroicons only at ~30+ distinct glyphs.
- **No animation libraries.** CSS transitions + `animate-pulse` suffice.
- **No marker clustering** when canvas markers + decimation handle the load (`leaflet.markercluster` only when grouping is a real interaction).
- **No multi-toast queue** until a project needs it.
- **No infinite zoom / unconstrained pan.** Set `maxBounds`. Most projects have a meaningful viewport.
- **No backend until profit/scale demands one.** Static-first: JSON in `docs/`, GitHub Pages. (levels.io: "you don't need a backend.")

---

## 14. When to revisit this document

- A new component pattern emerges across 2+ projects (promote from project `design.md` to here).
- A bullet in § 12 (pitfalls) repeats in a third project. That means it needs more emphasis or a different remedy.
- A new accessibility standard lands (WCAG update, platform-level mandate).
- A perf budget regresses across the portfolio (e.g. mid-range Android performance audit).

---

## Influences

- **FT, Bloomberg Businessweek, ProPublica, Greater Greater Washington**: editorial gravitas through typography and restraint, not dependencies.
- **Linear**: typography discipline, dark UI without losing readability.
- **Apple Human Interface Guidelines**: touch targets, safe areas, mobile-first ergonomics.
- **Pieter Levels (levels.io)**: "you don't need a backend, you don't need a CSS framework, you don't need a font, you don't need npm." When in doubt, ship the simpler thing.
- **Andrej Karpathy**: performance budgets are real constraints, not afterthoughts; measure before optimizing; the smallest version that works is the right starting point.
