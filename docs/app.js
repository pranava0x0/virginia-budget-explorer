/* Virginia Budget Explorer — vanilla JS, hand-rolled SVG charts, zero deps.
   Loads docs/data/budget.json (built + source-verified by scripts/build_data.py)
   and renders the KPI strip, donut, by-area table, over-time chart, quotes and
   sources. Charts are inline SVG so the page ships no charting library. */
"use strict";

// ---- single source of truth for area colors (mirrors the data's areas) ----
const THEME = {
  areaColors: {
    "Health & Human Resources": "#0b5fff",
    "K-12 Education": "#00b894",
    "Higher Education": "#6c5ce7",
    "Public Safety & Veterans": "#e17055",
    "Finance": "#0aa2c0",
    "Debt Service": "#94a3b8",
    "Commerce, Labor, Natural Resources & Agriculture": "#00cec9",
    "Administration & Central Accounts": "#f0a500",
    "Judicial & Other": "#fd79a8",
  },
  fallback: "#64748b",
};
const colorFor = (a) => THEME.areaColors[a] || THEME.fallback;

// ---- formatting ----
const fmtB = (millions, dp = 1) => "$" + (millions / 1000).toFixed(dp) + "B";
const fmtMoneyB = (millions) => (millions / 1000).toFixed(1);
const fmtM = (millions) => "$" + Math.round(millions).toLocaleString("en-US") + "M";
const fmtPct = (part, total, dp = 1) => (100 * part / total).toFixed(dp) + "%";
const shortArea = (a) => ({
  "Health & Human Resources": "Health & Human Res.",
  "K-12 Education": "K-12 Education",
  "Higher Education": "Higher Ed",
  "Public Safety & Veterans": "Public Safety & Vets",
  "Commerce, Labor, Natural Resources & Agriculture": "Commerce & Nat. Res.",
  "Administration & Central Accounts": "Admin & Central",
  "Judicial & Other": "Judicial & Other",
}[a] || a);

const el = (tag, attrs = {}, kids = []) => {
  const n = document.createElementNS(
    tag === "svg" || SVG_TAGS.has(tag) ? "http://www.w3.org/2000/svg" : "http://www.w3.org/1999/xhtml", tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.setAttribute("class", v);
    else if (k === "html") n.innerHTML = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on") && typeof v === "function") n.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) n.setAttribute(k, v);
  }
  for (const kid of [].concat(kids)) if (kid) n.appendChild(typeof kid === "string" ? document.createTextNode(kid) : kid);
  return n;
};
const SVG_TAGS = new Set(["g", "path", "circle", "line", "polyline", "text", "rect", "tspan"]);
const $ = (sel) => document.querySelector(sel);

// ---- state ----
let DATA = null;
let stage = "As amended"; // donut + table emphasis
let sortKey = "amended", sortDir = -1;

// ---- boot ----
(async function init() {
  try {
    const res = await fetch("data/budget.json", { cache: "no-cache" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    DATA = await res.json();
    if (!DATA.by_area || !DATA.by_area.length) return showState("empty");
    render();
  } catch (e) {
    console.error(e);
    showState("error", e.message);
  }
})();

function showState(kind, msg) {
  const root = $("#app");
  root.innerHTML = "";
  const map = {
    error: ["Couldn't load the budget data", msg || "Try refreshing the page."],
    empty: ["No budget data yet", "The dataset is empty. Run the build pipeline to populate it."],
  };
  const [h, p] = map[kind] || ["", ""];
  root.appendChild(el("div", { class: "state" }, [
    el("h2", { text: h }), el("p", { text: p }),
  ]));
}

// ---- derive per-area rows ----
function areaRows() {
  const byKey = {};
  for (const r of DATA.by_area) {
    byKey[r.area] = byKey[r.area] || { area: r.area };
    if (r.stage === "As adopted") byKey[r.area].adopted = r.millions;
    if (r.stage === "As amended") byKey[r.area].amended = r.millions;
    byKey[r.area].adopted_src = byKey[r.area].adopted_src || (r.stage === "As adopted" ? r : null);
  }
  const rows = DATA.areas.map((a) => {
    const o = byKey[a] || { area: a };
    o.delta = (o.amended ?? 0) - (o.adopted ?? 0);
    return o;
  });
  return rows;
}
const totalFor = (rows, key) => rows.reduce((s, r) => s + (r[key] || 0), 0);

// ---- top-level render ----
function render() {
  const root = $("#app");
  root.innerHTML = "";
  root.appendChild(heroSection());
  root.appendChild(allocationSection());
  root.appendChild(tableSection());
  root.appendChild(trendSection());
  root.appendChild(revenueSection());
  root.appendChild(quotesSection());
  root.appendChild(sourcesSection());
  $("#asof").textContent = "Data as of " + DATA.meta.captured_at;
}

// ---- hero + KPIs ----
function heroSection() {
  const rows = areaRows();
  const amended = totalFor(rows, "amended");
  const top = [...rows].sort((a, b) => (b.amended || 0) - (a.amended || 0))[0];
  const fy2628 = DATA.totals.find((t) => t.biennium === "FY2026-2028");

  const sec = el("section", { class: "hero wrap" });
  sec.appendChild(el("h1", { text: "Where Virginia's money goes" }));
  sec.appendChild(el("div", {
    class: "lede",
    text: "A plain-language look at the Commonwealth's general fund budget — every figure traced back to the official House Appropriations Committee documents, with the page number to prove it.",
  }));

  const kpis = el("div", { class: "kpis" });
  kpis.appendChild(kpiTile("Biennial general fund", fmtMoneyB(amended), "B", "FY2024-2026, as amended (Ch. 725)", false));
  kpis.appendChild(kpiTile("Biggest area", fmtMoneyB(top.amended), "B", top.area, false));
  kpis.appendChild(kpiTile("Spending areas", String(DATA.areas.length), "", "Secretarial areas tracked", true));
  if (fy2628) kpis.appendChild(kpiTile("Next biennium", String(fy2628.billions), "B", "FY2026-2028 GF resources (HB 30)", true));
  sec.appendChild(kpis);
  return sec;
}
function kpiTile(label, value, unit, sub, accent) {
  return el("div", { class: "kpi" + (accent ? " accent" : "") }, [
    el("div", { class: "k-label", text: label }),
    el("div", { class: "k-value num" }, [document.createTextNode(value), unit ? el("span", { class: "unit", text: unit }) : null]),
    el("div", { class: "k-sub", text: sub }),
  ]);
}

// ---- allocation (donut + legend) ----
function allocationSection() {
  const sec = el("section", { class: "wrap" });
  sec.appendChild(sectionHead("Where it goes", "General fund spending by area",
    "Share of the FY2024-2026 general fund operating budget. Tap a slice to focus it."));

  const toggle = el("div", { class: "pills", role: "group", "aria-label": "Budget stage" }, [
    pillBtn("As adopted", "Ch. 2 (2024)"),
    pillBtn("As amended", "Ch. 725 (2025)"),
  ]);
  const panel = el("div", { class: "panel" });
  panel.appendChild(el("div", { style: "margin-bottom:18px" }, [toggle]));
  const host = el("div", { class: "donut-host" });
  panel.appendChild(host);
  sec.appendChild(panel);
  drawDonut(host);
  return sec;
}
function pillBtn(value, label) {
  return el("button", {
    class: "pill", type: "button", "aria-pressed": String(stage === value),
    onclick: () => { stage = value; render(); document.getElementById("alloc-anchor")?.scrollIntoView(); },
  }, [label]);
}
function drawDonut(host) {
  host.innerHTML = "";
  const key = stage === "As adopted" ? "adopted" : "amended";
  const rows = areaRows().map((r) => ({ area: r.area, val: r[key] || 0 }))
    .filter((r) => r.val > 0).sort((a, b) => b.val - a.val);
  const total = rows.reduce((s, r) => s + r.val, 0);

  const size = 240, sw = 34, r = (size - sw) / 2, cx = size / 2, cy = size / 2, C = 2 * Math.PI * r;
  const svg = el("svg", { class: "donut", viewBox: `0 0 ${size} ${size}`, role: "img",
    "aria-label": `General fund spending by area, ${stage}, total ${fmtB(total)}` });
  svg.appendChild(el("circle", { cx, cy, r, fill: "none", stroke: "#eef3f9", "stroke-width": sw }));
  let acc = 0;
  rows.forEach((row, i) => {
    const frac = row.val / total, seg = frac * C;
    const circ = el("circle", {
      class: "slice", cx, cy, r, fill: "none", stroke: colorFor(row.area), "stroke-width": sw,
      "stroke-dasharray": `${seg} ${C - seg}`, "stroke-dashoffset": -acc,
      "data-area": row.area,
      "aria-label": `${row.area}: ${fmtB(row.val)}, ${fmtPct(row.val, total)}`,
    });
    circ.addEventListener("mouseenter", () => focusArea(row.area));
    circ.addEventListener("mouseleave", () => focusArea(null));
    circ.addEventListener("click", () => focusArea(row.area, true));
    svg.appendChild(circ);
    acc += seg;
  });
  const center = el("g", { class: "donut-center" });
  center.appendChild(el("text", { x: cx, y: cy - 4, "text-anchor": "middle", class: "c-val num", text: fmtB(total) }));
  center.appendChild(el("text", { x: cx, y: cy + 16, "text-anchor": "middle", class: "c-lab", text: "GF · " + stage }));
  svg.appendChild(center);

  const legend = el("div", { class: "legend", role: "list" });
  rows.forEach((row) => {
    const btn = el("button", { class: "legend-row", type: "button", role: "listitem", "data-area": row.area,
      onclick: () => focusArea(row.area, true),
      onmouseenter: () => focusArea(row.area), onmouseleave: () => focusArea(null) }, [
      el("span", { class: "dot", style: `background:${colorFor(row.area)}` }),
      el("span", { class: "lname", text: row.area }),
      el("span", { class: "lval num", text: fmtB(row.val) }),
      el("span", { class: "lpct num", text: fmtPct(row.val, total) }),
    ]);
    legend.appendChild(btn);
  });
  const wrap = el("div", { class: "donut-wrap", id: "alloc-anchor" }, [svg, legend]);
  host.appendChild(wrap);
}
let pinnedArea = null;
function focusArea(area, pin = false) {
  if (pin) pinnedArea = pinnedArea === area ? null : area;
  const active = pin ? pinnedArea : (pinnedArea || area);
  document.querySelectorAll(".donut").forEach((d) => d.classList.toggle("has-active", !!active));
  document.querySelectorAll("[data-area]").forEach((n) => {
    const on = active && n.getAttribute("data-area") === active;
    n.classList.toggle("active", !!on);
  });
}

// ---- table ----
function tableSection() {
  const sec = el("section", { class: "wrap" });
  sec.appendChild(sectionHead("The receipts", "Every area, both budget versions",
    "General fund, $ in billions. “Change” compares the amended budget (Ch. 725) to what was first adopted (Ch. 2)."));
  const rows = areaRows();
  const adoptedTot = totalFor(rows, "adopted"), amendedTot = totalFor(rows, "amended");

  const sorters = {
    area: (a, b) => a.area.localeCompare(b.area),
    adopted: (a, b) => (a.adopted || 0) - (b.adopted || 0),
    amended: (a, b) => (a.amended || 0) - (b.amended || 0),
    delta: (a, b) => a.delta - b.delta,
  };
  const sorted = [...rows].sort((a, b) => sortDir * sorters[sortKey](a, b));

  const th = (key, label) => el("th", { scope: "col", tabindex: "0", role: "columnheader",
    "aria-sort": sortKey === key ? (sortDir > 0 ? "ascending" : "descending") : "none",
    onclick: () => setSort(key), onkeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSort(key); } },
  }, [label + " ", sortKey === key ? el("span", { class: "arrow", text: sortDir > 0 ? "▲" : "▼" }) : null]);

  const thead = el("thead", {}, [el("tr", {}, [
    th("area", "Area"), th("adopted", "Adopted"), th("amended", "Amended"), th("delta", "Change"),
    el("th", { scope: "col", text: "Share" }),
  ])]);
  const tbody = el("tbody");
  sorted.forEach((r) => {
    const up = r.delta >= 0;
    tbody.appendChild(el("tr", { "data-area": r.area,
      onmouseenter: () => focusArea(r.area), onmouseleave: () => focusArea(null) }, [
      el("td", {}, [el("span", { class: "area-cell" }, [
        el("span", { class: "dot", style: `background:${colorFor(r.area)}` }), shortArea(r.area)])]),
      el("td", { class: "num", text: r.adopted ? fmtB(r.adopted) : "—" }),
      el("td", { class: "num big", text: r.amended ? fmtB(r.amended) : "—" }),
      el("td", { class: "num delta " + (up ? "up" : "down"),
        text: (up ? "▲ " : "▼ ") + fmtM(Math.abs(r.delta)) }),
      el("td", { class: "num", text: fmtPct(r.amended || 0, amendedTot) }),
    ]));
  });
  const tfoot = el("tfoot", {}, [el("tr", {}, [
    el("td", { text: "Total general fund" }),
    el("td", { class: "num", text: fmtB(adoptedTot) }),
    el("td", { class: "num", text: fmtB(amendedTot) }),
    el("td", { class: "num delta up", text: "▲ " + fmtM(amendedTot - adoptedTot) }),
    el("td", { class: "num", text: "100%" }),
  ])]);
  const table = el("table", { class: "budget" }, [thead, tbody, tfoot]);
  sec.appendChild(el("div", { class: "panel" }, [el("div", { class: "table-scroll" }, [table])]));
  return sec;
}
function setSort(key) { if (sortKey === key) sortDir *= -1; else { sortKey = key; sortDir = key === "area" ? 1 : -1; } render(); }

// ---- over-time trend (slope chart) ----
function trendSection() {
  const sec = el("section", { class: "wrap" });
  sec.appendChild(sectionHead("Over time", "How each area changed, adopted → amended",
    "FY2024-2026 general fund by area, from the budget as first adopted (May 2024) to as amended (May 2025). Tap an area to isolate its line."));
  const panel = el("div", { class: "panel" });
  const host = el("div", { class: "trend-host" });
  panel.appendChild(host);
  sec.appendChild(panel);
  drawTrend(host);
  return sec;
}
function drawTrend(host) {
  host.innerHTML = "";
  const stages = [
    { key: "adopted", label: "Adopted", sub: "Ch. 2 · May 2024" },
    { key: "amended", label: "Amended", sub: "Ch. 725 · May 2025" },
  ];
  const rows = areaRows().filter((r) => r.adopted || r.amended);
  const maxV = Math.max(...rows.map((r) => Math.max(r.adopted || 0, r.amended || 0)));
  const niceMax = Math.ceil(maxV / 5000) * 5000;

  const W = 720, H = 440, m = { t: 22, r: 152, b: 48, l: 50 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const X = (i) => m.l + (stages.length === 1 ? iw / 2 : (i / (stages.length - 1)) * iw);
  const Y = (v) => m.t + ih - (v / niceMax) * ih;

  const svg = el("svg", { class: "chart-svg", viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": "General fund by area, adopted versus amended" });
  // gridlines + y ticks
  for (let g = 0; g <= 4; g++) {
    const v = (niceMax / 4) * g, y = Y(v);
    svg.appendChild(el("line", { class: "gridline", x1: m.l, y1: y, x2: m.l + iw, y2: y }));
    svg.appendChild(el("text", { class: "tick num", x: m.l - 8, y: y + 4, "text-anchor": "end", text: "$" + (v / 1000).toFixed(0) + "B" }));
  }
  // x labels
  stages.forEach((s, i) => {
    svg.appendChild(el("text", { class: "xlab", x: X(i), y: H - 22, "text-anchor": "middle", text: s.label }));
    svg.appendChild(el("text", { class: "tick", x: X(i), y: H - 8, "text-anchor": "middle", text: s.sub }));
  });
  // series
  const labelPos = [];
  rows.sort((a, b) => (b.amended || 0) - (a.amended || 0)).forEach((r) => {
    const c = colorFor(r.area);
    const pts = stages.map((s, i) => ({ x: X(i), y: Y(r[s.key] || 0), v: r[s.key] || 0 }));
    svg.appendChild(el("polyline", { class: "serie", "data-area": r.area, stroke: c,
      points: pts.map((p) => `${p.x},${p.y}`).join(" ") }));
    pts.forEach((p) => svg.appendChild(el("circle", { class: "dot", "data-area": r.area, cx: p.x, cy: p.y, r: 4.5, fill: c })));
    const end = pts[pts.length - 1];
    labelPos.push({ area: r.area, y: end.y, oy: end.y, x: end.x, c, v: end.v });
  });
  // de-collide the two-line right-edge labels: push down by min gap, then if the
  // stack overflows the plot, shift it up so every label stays on-canvas.
  labelPos.sort((a, b) => a.y - b.y);
  const minGap = 27, maxY = m.t + ih, last = labelPos.length - 1;
  // pass 1: push down so labels don't overlap
  for (let i = 1; i <= last; i++)
    if (labelPos[i].y - labelPos[i - 1].y < minGap) labelPos[i].y = labelPos[i - 1].y + minGap;
  // pass 2: if the stack ran past the bottom, pin the last label and relax the
  // dense cluster UPWARD into the empty space above it (keeps the well-spaced
  // top labels sitting on their own data points instead of dragging them up).
  if (labelPos[last].y > maxY) {
    labelPos[last].y = maxY;
    for (let i = last - 1; i >= 0; i--)
      if (labelPos[i].y > labelPos[i + 1].y - minGap) labelPos[i].y = labelPos[i + 1].y - minGap;
  }
  labelPos.forEach((l) => {
    const g = el("g", { class: "dlabel", "data-area": l.area });
    // faint leader line from the line's endpoint to its (possibly moved) label
    g.appendChild(el("polyline", { fill: "none", stroke: l.c, "stroke-width": 1, opacity: .5,
      points: `${l.x + 3},${l.oy} ${l.x + 9},${l.y - 4} ${l.x + 14},${l.y - 4}` }));
    g.appendChild(el("text", { x: l.x + 18, y: l.y - 1, fill: l.c, "font-weight": "800", text: shortArea(l.area) }));
    g.appendChild(el("text", { x: l.x + 18, y: l.y + 12, fill: "#7c8a98", class: "num", "font-size": "10", text: fmtB(l.v) }));
    svg.appendChild(g);
  });
  // interactions
  svg.querySelectorAll("[data-area]").forEach((n) => {
    const a = n.getAttribute("data-area");
    n.addEventListener("mouseenter", () => trendFocus(svg, a));
    n.addEventListener("mouseleave", () => trendFocus(svg, null));
    if (n.tagName === "polyline") n.addEventListener("click", () => trendFocus(svg, a));
  });

  // chips legend
  const chips = el("div", { class: "legend", style: "flex-direction:row;flex-wrap:wrap;gap:6px;margin-top:14px" });
  rows.forEach((r) => {
    chips.appendChild(el("button", { class: "legend-row", type: "button",
      style: "width:auto;display:inline-flex;gap:7px;padding:7px 11px",
      onmouseenter: () => trendFocus(svg, r.area), onmouseleave: () => trendFocus(svg, null),
      onclick: () => trendFocus(svg, r.area) }, [
      el("span", { class: "dot", style: `background:${colorFor(r.area)}` }),
      el("span", { class: "lname", style: "max-width:none", text: shortArea(r.area) }),
    ]));
  });
  host.appendChild(svg);
  host.appendChild(chips);
}
let trendPinned = null;
function trendFocus(svg, area) {
  trendPinned = area;
  svg.classList.toggle("has-active", !!area);
  svg.querySelectorAll("[data-area]").forEach((n) =>
    n.classList.toggle("active", !!area && n.getAttribute("data-area") === area));
}

// ---- revenue / resources snapshot ----
function revenueSection() {
  const sec = el("section", { class: "wrap" });
  sec.appendChild(sectionHead("Where it comes from", "General fund resources, FY2026",
    "How the FY2026 general fund is funded (Virginia in Focus). Bars scaled to the largest source."));
  const items = DATA.gf_resources_fy2026 || [];
  if (!items.length) return sec;
  const max = Math.max(...items.map((i) => i.millions));
  const list = el("div", { style: "display:flex;flex-direction:column;gap:12px" });
  items.forEach((it, idx) => {
    const pct = (it.millions / max) * 100;
    list.appendChild(el("div", {}, [
      el("div", { style: "display:flex;justify-content:space-between;font-size:13.5px;font-weight:700;margin-bottom:5px" }, [
        el("span", { text: it.label }), el("span", { class: "num", text: fmtB(it.millions) })]),
      el("div", { style: "background:#eef3f9;border-radius:999px;height:14px;overflow:hidden" }, [
        el("div", { style: `width:${pct}%;height:100%;border-radius:999px;background:${idx === 0 ? "var(--brand)" : "var(--accent)"}` })]),
    ]));
  });
  sec.appendChild(el("div", { class: "panel" }, [list]));
  return sec;
}

// ---- quotes ----
function quotesSection() {
  const sec = el("section", { class: "wrap" });
  sec.appendChild(sectionHead("In their words", "Policy principles, with page citations",
    "Every quote is verbatim from the official document and links to the exact page."));
  const grid = el("div", { class: "quote-grid" });
  DATA.quotes.forEach((q) => {
    const src = DATA.sources.find((s) => s.stem === q.source_stem);
    const href = src ? src.url + "#page=" + q.page : "#";
    grid.appendChild(el("div", { class: "qcard" }, [
      el("span", { class: "topic", text: q.topic }),
      el("blockquote", { text: q.text }),
      el("div", { class: "principle", text: q.principle }),
      el("div", { class: "cite" }, [
        el("a", { class: "page-chip", href, target: "_blank", rel: "noopener",
          "aria-label": `Open ${q.doc_title} at page ${q.page}` }, ["p. " + q.page + " ↗"]),
        el("span", { class: "src", text: q.doc_title }),
      ]),
    ]));
  });
  sec.appendChild(grid);
  return sec;
}

// ---- sources ----
function sourcesSection() {
  const sec = el("section", { class: "wrap" });
  sec.appendChild(sectionHead("Sources", "Official documents behind every number", ""));
  const grid = el("div", { class: "src-grid" });
  DATA.sources.forEach((s) => {
    grid.appendChild(el("div", { class: "src-card" }, [
      el("div", { class: "badge", text: s.biennium + " · " + s.stage }),
      el("h3", { text: s.title }),
      el("div", { class: "meta", text: `${s.publisher} · ${s.page_count} pp · as of ${s.as_of}` }),
      el("div", { style: "margin-top:10px" }, [
        el("a", { href: s.url, target: "_blank", rel: "noopener", text: "Open document ↗" })]),
    ]));
  });
  sec.appendChild(grid);
  return sec;
}

// ---- shared ----
function sectionHead(eyebrow, title, desc) {
  return el("div", { class: "section-head" }, [
    el("span", { class: "eyebrow", text: eyebrow }),
    el("h2", { text: title }),
    desc ? el("p", { text: desc }) : null,
  ]);
}
