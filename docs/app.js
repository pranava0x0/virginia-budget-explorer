/* Virginia Budget Explorer — vanilla JS, hand-rolled SVG charts, zero deps.
   Tabbed layout. Every figure shows a source + page citation, and a build-time
   validator (scripts/validate.py -> validation.json) confirms each point
   against its source page. */
"use strict";

// ---- single source of truth for area colors ----
const THEME = {
  areaColors: {
    "Health & Human Resources": "#0064e0",
    "K-12 Education": "#1d9b46",
    "Higher Education": "#7c4dff",
    "Public Safety & Veterans": "#f5871f",
    "Finance": "#0098b3",
    "Debt Service": "#8a96a3",
    "Commerce, Labor, Natural Resources & Agriculture": "#12b2b8",
    "Administration & Central Accounts": "#e0a800",
    "Judicial & Other": "#e84393",
  },
  fallback: "#65676b",
};
const colorFor = (a) => THEME.areaColors[a] || THEME.fallback;

// short doc labels for citations
const DOC_SHORT = {
  "overview_2024_fy2024-2026": "Overview FY24-26",
  "overview_2025_ch725": "Ch. 725 Overview",
  "overview_2026_fy2026-2028": "Overview FY26-28",
  "conf_report_hb30_2026": "HB 30 Conf. Report",
  "virginia_in_focus_2026": "Virginia in Focus",
};

// ---- formatting ----
const fmtB = (m, dp = 1) => "$" + (m / 1000).toFixed(dp) + "B";
const fmtMoneyB = (m) => (m / 1000).toFixed(1);
const fmtM = (m) => "$" + Math.round(m).toLocaleString("en-US") + "M";
const fmtPct = (part, total, dp = 1) => (100 * part / total).toFixed(dp) + "%";
const shortArea = (a) => ({
  "Health & Human Resources": "Health & Human Res.",
  "Higher Education": "Higher Ed",
  "Public Safety & Veterans": "Public Safety & Vets",
  "Commerce, Labor, Natural Resources & Agriculture": "Commerce & Nat. Res.",
  "Administration & Central Accounts": "Admin & Central",
}[a] || a);
const biShort = (b) => b.replace("FY20", "FY").replace("-20", "-");

const SVG_TAGS = new Set(["svg", "g", "path", "circle", "line", "polyline", "text", "rect", "tspan"]);
const el = (tag, attrs = {}, kids = []) => {
  const n = SVG_TAGS.has(tag)
    ? document.createElementNS("http://www.w3.org/2000/svg", tag)
    : document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined) continue;
    if (k === "class") n.setAttribute("class", v);
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on") && typeof v === "function") n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v);
  }
  for (const kid of [].concat(kids)) if (kid) n.appendChild(typeof kid === "string" ? document.createTextNode(kid) : kid);
  return n;
};
const $ = (s) => document.querySelector(s);

// ---- citations ----
function srcUrl(stem, page) {
  const s = (DATA.sources || []).find((x) => x.stem === stem);
  return s ? s.url + "#page=" + page : "#";
}
function cite(stem, page, opts = {}) {
  const label = (opts.short ? "" : DOC_SHORT[stem] + " · ") + "p. " + page;
  return el("a", {
    class: "cite", href: srcUrl(stem, page), target: "_blank", rel: "noopener",
    title: `Open ${DOC_SHORT[stem]} at page ${page}`,
    "aria-label": `Source: ${DOC_SHORT[stem]}, page ${page}`,
  }, [label + " ↗"]);
}

// ---- state ----
let DATA = null, VALIDATION = null;
let stage = "As amended";
let sortKey = "amended", sortDir = -1;
let activeTab = "overview";
let pinnedArea = null, trendPinned = null;

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "trends", label: "Trends" },
  { id: "funding", label: "Funding" },
  { id: "nextyear", label: "Next year" },
  { id: "sources", label: "Sources" },
];

// ---- boot ----
(async function init() {
  try {
    const [bRes, vRes] = await Promise.all([
      fetch("data/budget.json", { cache: "no-cache" }),
      fetch("data/validation.json", { cache: "no-cache" }).catch(() => null),
    ]);
    if (!bRes.ok) throw new Error("HTTP " + bRes.status);
    DATA = await bRes.json();
    if (vRes && vRes.ok) VALIDATION = await vRes.json();
    if (!DATA.by_area || !DATA.by_area.length) return showState("empty");
    renderShell();
  } catch (e) {
    console.error(e);
    showState("error", e.message);
  }
})();

function showState(kind, msg) {
  const root = $("#app");
  root.innerHTML = "";
  const m = {
    error: ["Couldn't load the budget data", msg || "Try refreshing."],
    empty: ["No budget data yet", "Run the build pipeline to populate it."],
  }[kind] || ["", ""];
  root.appendChild(el("div", { class: "state" }, [el("h2", { text: m[0] }), el("p", { text: m[1] })]));
}

// ---- derive per-area rows across all stages ----
function recordFor(area, stageName) {
  return DATA.by_area.find((r) => r.area === area && r.stage === stageName);
}
function areaRows() {
  return DATA.areas.map((a) => {
    const ad = recordFor(a, "As adopted"), am = recordFor(a, "As amended"), nx = recordFor(a, "As introduced");
    return {
      area: a,
      adopted: ad ? ad.millions : 0, amended: am ? am.millions : 0, introduced: nx ? nx.millions : 0,
      srcAdopted: ad, srcAmended: am, srcNext: nx,
      delta: (am ? am.millions : 0) - (ad ? ad.millions : 0),
      deltaNext: (nx ? nx.millions : 0) - (am ? am.millions : 0),
    };
  });
}
const totalFor = (rows, key) => rows.reduce((s, r) => s + (r[key] || 0), 0);

// time points for the trend chart (ordered by source date)
function timePoints() {
  const seen = {};
  DATA.by_area.forEach((r) => {
    const k = r.biennium + "|" + r.stage;
    if (!seen[k]) seen[k] = { key: k, biennium: r.biennium, stage: r.stage, as_of: r.as_of };
  });
  return Object.values(seen).sort((a, b) => (a.as_of < b.as_of ? -1 : 1))
    .map((t) => ({ ...t, main: biShort(t.biennium), sub: t.stage.replace("As ", "") }));
}

// ---- shell (hero + tabs) ----
function selectTab(id, focus) {
  activeTab = id;
  renderShell();
  if (focus) { const b = document.getElementById("tab-" + id); if (b) b.focus(); }
}
function onTabKey(e) {
  const i = TABS.findIndex((t) => t.id === activeTab);
  let j = null;
  if (e.key === "ArrowRight" || e.key === "ArrowDown") j = (i + 1) % TABS.length;
  else if (e.key === "ArrowLeft" || e.key === "ArrowUp") j = (i - 1 + TABS.length) % TABS.length;
  else if (e.key === "Home") j = 0;
  else if (e.key === "End") j = TABS.length - 1;
  if (j !== null) { e.preventDefault(); selectTab(TABS[j].id, true); }
}
function renderShell() {
  const root = $("#app");
  root.innerHTML = "";
  root.appendChild(heroBlock());
  const tabbar = el("div", { class: "tabbar", role: "tablist", "aria-label": "Budget views", onkeydown: onTabKey });
  TABS.forEach((t) => {
    const on = activeTab === t.id;
    tabbar.appendChild(el("button", {
      class: "tab" + (on ? " active" : ""), type: "button", role: "tab", id: "tab-" + t.id,
      "aria-selected": String(on), "aria-controls": "panel-" + t.id, tabindex: on ? "0" : "-1",
      onclick: () => selectTab(t.id, false),
    }, [t.label]));
  });
  root.appendChild(el("div", { class: "wrap" }, [tabbar]));
  const content = el("div", { class: "tab-content", role: "tabpanel", id: "panel-" + activeTab,
    "aria-labelledby": "tab-" + activeTab, tabindex: "0" });
  root.appendChild(content);
  pinnedArea = null; trendPinned = null;
  ({ overview: tabOverview, trends: tabTrends, funding: tabFunding,
     nextyear: tabNextYear, sources: tabSources }[activeTab])(content);
  const asof = $("#asof");
  if (asof) asof.textContent = "Data as of " + (DATA.meta.data_as_of || DATA.meta.built_at);
}

function heroBlock() {
  const sec = el("section", { class: "hero wrap" });
  sec.appendChild(el("h1", { text: "Where Virginia's money goes" }));
  sec.appendChild(el("p", { class: "lede",
    text: "A plain-language look at the Commonwealth's general fund budget — every figure traced to an official House Appropriations Committee document, down to the page." }));
  if (VALIDATION) {
    sec.appendChild(el("p", { class: "verified-note", title: "Checked by scripts/validate.py" }, [
      el("span", { class: "vcheck", "aria-hidden": "true", text: "✓ " }),
      `Every figure and quote checked against its source page — ${VALIDATION.passed}/${VALIDATION.total}, ${VALIDATION.validated_on}`,
    ]));
  }
  return sec;
}

// ---- shared bits ----
function sectionHead(_eyebrow, title, desc) {
  // plain title + lede — no decorative kicker label
  return el("div", { class: "section-head" }, [
    el("h2", { text: title }),
    desc ? el("p", { text: desc }) : null,
  ]);
}
function kpiTile(label, value, unit, sub, accent, citeNode) {
  return el("div", { class: "kpi" + (accent ? " accent" : "") }, [
    el("div", { class: "k-label", text: label }),
    el("div", { class: "k-value num" }, [document.createTextNode(value), unit ? el("span", { class: "unit", text: unit }) : null]),
    el("div", { class: "k-sub", text: sub }),
    citeNode ? el("div", { class: "k-cite" }, [citeNode]) : null,
  ]);
}

// ============================ OVERVIEW TAB ============================
function tabOverview(root) {
  const rows = areaRows();
  const amended = totalFor(rows, "amended");
  const top = [...rows].sort((a, b) => b.amended - a.amended)[0];
  const fySpend = DATA.totals.find((t) => t.biennium === "FY2026-2028" && t.kind === "GF spending");
  const statedAm = DATA.totals.find((t) => t.biennium === "FY2024-2026" && t.stage === "As amended");

  const kpis = el("div", { class: "kpis wrap" });
  kpis.appendChild(kpiTile("Biennial general fund", fmtMoneyB(amended), "B", "FY2024-2026, amended", false,
    statedAm ? cite(statedAm.source_stem, statedAm.page, { short: true }) : null));
  kpis.appendChild(kpiTile("Biggest area", fmtMoneyB(top.amended), "B", top.area, false,
    top.srcAmended ? cite(top.srcAmended.source_stem, top.srcAmended.page, { short: true }) : null));
  kpis.appendChild(kpiTile("Spending areas", String(DATA.areas.length), "", "Secretarial areas", true, null));
  if (fySpend) kpis.appendChild(kpiTile("Next biennium", String(fySpend.billions), "B", "FY2026-2028 (HB 30)", true,
    cite(fySpend.source_stem, fySpend.page, { short: true })));
  root.appendChild(kpis);

  const sec = el("section", { class: "wrap" });
  sec.appendChild(sectionHead("Where it goes", "General fund spending by area",
    "Share of the FY2024-2026 general fund operating budget. Tap a slice to focus it."));
  const panel = el("div", { class: "panel" });
  const toggle = el("div", { class: "pills", role: "group", "aria-label": "Budget stage" }, [
    pillBtn("As adopted", "Adopted (Ch. 2)"), pillBtn("As amended", "Amended (Ch. 725)"),
  ]);
  panel.appendChild(el("div", { style: "margin-bottom:16px" }, [toggle]));
  const host = el("div", {});
  panel.appendChild(host);
  sec.appendChild(panel);
  root.appendChild(sec);
  drawDonutForStage(host, stage);

  root.appendChild(overviewTableSection(rows));
}
function pillBtn(value, label) {
  return el("button", {
    class: "pill", type: "button", "aria-pressed": String(stage === value),
    onclick: () => { stage = value; renderShell(); },
  }, [label]);
}

function donutRows(stageName) {
  const key = { "As adopted": "adopted", "As amended": "amended", "As introduced": "introduced" }[stageName];
  return areaRows().map((r) => ({ area: r.area, val: r[key] || 0,
      src: stageName === "As introduced" ? r.srcNext : stageName === "As adopted" ? r.srcAdopted : r.srcAmended }))
    .filter((r) => r.val > 0).sort((a, b) => b.val - a.val);
}
function drawDonutForStage(host, stageName) {
  const rows = donutRows(stageName);
  const total = rows.reduce((s, r) => s + r.val, 0);
  const src = rows[0] && rows[0].src;
  drawDonut(host, rows, stageName, total, src);
}
function drawDonut(host, rows, centerSub, total, src) {
  host.innerHTML = "";
  const size = 240, sw = 34, r = (size - sw) / 2, cx = size / 2, cy = size / 2, C = 2 * Math.PI * r;
  const svg = el("svg", { class: "donut", viewBox: `0 0 ${size} ${size}`, role: "img",
    "aria-label": `Spending by area, total ${fmtB(total)}` });
  svg.appendChild(el("circle", { cx, cy, r, fill: "none", stroke: "#e9edf2", "stroke-width": sw }));
  let acc = 0;
  rows.forEach((row) => {
    const seg = (row.val / total) * C;
    const c = el("circle", { class: "slice", cx, cy, r, fill: "none", stroke: colorFor(row.area),
      "stroke-width": sw, "stroke-dasharray": `${seg} ${C - seg}`, "stroke-dashoffset": -acc, "data-area": row.area,
      "aria-label": `${row.area}: ${fmtB(row.val)}, ${fmtPct(row.val, total)}` });
    c.addEventListener("mouseenter", () => focusArea(row.area));
    c.addEventListener("mouseleave", () => focusArea(null));
    c.addEventListener("click", () => focusArea(row.area, true));
    svg.appendChild(c); acc += seg;
  });
  svg.appendChild(el("text", { x: cx, y: cy - 2, "text-anchor": "middle", class: "c-val num", text: fmtB(total) }));
  svg.appendChild(el("text", { x: cx, y: cy + 16, "text-anchor": "middle", class: "c-lab", text: centerSub }));

  const legend = el("div", { class: "legend", role: "list" });
  rows.forEach((row) => {
    legend.appendChild(el("button", { class: "legend-row", type: "button", role: "listitem", "data-area": row.area,
      onclick: () => focusArea(row.area, true),
      onmouseenter: () => focusArea(row.area), onmouseleave: () => focusArea(null) }, [
      el("span", { class: "dot", style: `background:${colorFor(row.area)}` }),
      el("span", { class: "lname", text: shortArea(row.area) }),
      el("span", { class: "lval num", text: fmtB(row.val) }),
      el("span", { class: "lpct num", text: fmtPct(row.val, total) }),
    ]));
  });
  host.appendChild(el("div", { class: "donut-wrap" }, [svg, legend]));
  if (src) host.appendChild(el("div", { class: "chart-cite" }, ["Source: ", cite(src.source_stem, src.page)]));
}
function focusArea(area, pin = false) {
  if (pin) pinnedArea = pinnedArea === area ? null : area;
  const active = pin ? pinnedArea : (pinnedArea || area);
  document.querySelectorAll(".donut").forEach((d) => d.classList.toggle("has-active", !!active));
  document.querySelectorAll("[data-area]").forEach((n) =>
    n.classList.toggle("active", !!active && n.getAttribute("data-area") === active));
}

function overviewTableSection(rows) {
  const sec = el("section", { class: "wrap" });
  sec.appendChild(sectionHead("", "Detail by area",
    "General fund, $ in billions. “Change” compares amended (Ch. 725) to adopted (Ch. 2). Each row links to its source page."));
  const adoptedTot = totalFor(rows, "adopted"), amendedTot = totalFor(rows, "amended");
  const sorters = { area: (a, b) => a.area.localeCompare(b.area), adopted: (a, b) => a.adopted - b.adopted,
    amended: (a, b) => a.amended - b.amended, delta: (a, b) => a.delta - b.delta };
  const sorted = [...rows].sort((a, b) => sortDir * sorters[sortKey](a, b));
  const th = (key, label) => el("th", { scope: "col", tabindex: "0", role: "columnheader",
    "aria-sort": sortKey === key ? (sortDir > 0 ? "ascending" : "descending") : "none",
    onclick: () => setSort(key), onkeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSort(key); } },
  }, [label + " ", sortKey === key ? el("span", { class: "arrow", text: sortDir > 0 ? "▲" : "▼" }) : null]);
  const thead = el("thead", {}, [el("tr", {}, [
    th("area", "Area"), th("adopted", "Adopted"), th("amended", "Amended"), th("delta", "Change"),
    el("th", { scope: "col", text: "Share" }), el("th", { scope: "col", text: "Source" }),
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
      el("td", { class: "num delta " + (up ? "up" : "down"), text: (up ? "▲ " : "▼ ") + fmtM(Math.abs(r.delta)) }),
      el("td", { class: "num", text: fmtPct(r.amended || 0, amendedTot) }),
      el("td", {}, [r.srcAmended ? cite(r.srcAmended.source_stem, r.srcAmended.page, { short: true }) : "—"]),
    ]));
  });
  const tfoot = el("tfoot", {}, [el("tr", {}, [
    el("td", { text: "Total general fund" }),
    el("td", { class: "num", text: fmtB(adoptedTot) }),
    el("td", { class: "num", text: fmtB(amendedTot) }),
    el("td", { class: "num delta up", text: "▲ " + fmtM(amendedTot - adoptedTot) }),
    el("td", { class: "num", text: "100%" }), el("td", {}, [""]),
  ])]);
  const caption = el("caption", { class: "visually-hidden",
    text: "General fund spending by secretarial area for FY2024-2026, comparing the adopted and amended budgets, in billions of dollars." });
  sec.appendChild(el("div", { class: "panel" }, [el("div", { class: "table-scroll" },
    [el("table", { class: "budget overview-cols" }, [caption, thead, tbody, tfoot])])]));
  return sec;
}
function setSort(key) { if (sortKey === key) sortDir *= -1; else { sortKey = key; sortDir = key === "area" ? 1 : -1; } renderShell(); }

// ============================ TRENDS TAB ============================
function tabTrends(root) {
  const sec = el("section", { class: "wrap" });
  sec.appendChild(sectionHead("", "Spending by area, over time",
    "From the FY2024-2026 budget as adopted and amended, through the FY2026-2028 budget as introduced. Tap an area to isolate its line."));
  const panel = el("div", { class: "panel" });
  const host = el("div", {});
  panel.appendChild(host);
  sec.appendChild(panel);
  root.appendChild(sec);
  drawTrend(host);
}
function drawTrend(host) {
  host.innerHTML = "";
  const pts = timePoints();
  const rows = areaRows();
  const valAt = (area, tp) => {
    const rec = DATA.by_area.find((r) => r.area === area && r.biennium === tp.biennium && r.stage === tp.stage);
    return rec ? rec.millions : null;
  };
  const maxV = Math.max(...DATA.by_area.map((r) => r.millions));
  const niceMax = Math.ceil(maxV / 5000) * 5000;
  const W = 720, H = 440, m = { t: 22, r: 156, b: 50, l: 52 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const X = (i) => m.l + (pts.length === 1 ? iw / 2 : (i / (pts.length - 1)) * iw);
  const Y = (v) => m.t + ih - (v / niceMax) * ih;

  const svg = el("svg", { class: "chart-svg", viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": "General fund by area across budgets" });
  for (let g = 0; g <= 5; g++) {
    const v = (niceMax / 5) * g, y = Y(v);
    svg.appendChild(el("line", { class: "gridline", x1: m.l, y1: y, x2: m.l + iw, y2: y }));
    svg.appendChild(el("text", { class: "tick num", x: m.l - 8, y: y + 4, "text-anchor": "end", text: "$" + (v / 1000).toFixed(0) + "B" }));
  }
  pts.forEach((p, i) => {
    svg.appendChild(el("text", { class: "xlab", x: X(i), y: H - 24, "text-anchor": "middle", text: p.main }));
    svg.appendChild(el("text", { class: "tick", x: X(i), y: H - 9, "text-anchor": "middle", text: p.sub }));
  });
  const labelPos = [];
  rows.sort((a, b) => b.introduced - a.introduced).forEach((r) => {
    const c = colorFor(r.area);
    const series = pts.map((p, i) => ({ x: X(i), y: Y(valAt(r.area, p) || 0), v: valAt(r.area, p) }))
      .filter((s) => s.v != null);
    if (!series.length) return;
    svg.appendChild(el("polyline", { class: "serie", "data-area": r.area, stroke: c,
      points: series.map((s) => `${s.x},${s.y}`).join(" ") }));
    series.forEach((s) => svg.appendChild(el("circle", { class: "dot", "data-area": r.area, cx: s.x, cy: s.y, r: 4.5, fill: c })));
    const last = series[series.length - 1];
    labelPos.push({ area: r.area, y: last.y, oy: last.y, x: last.x, c, v: last.v });
  });
  labelPos.sort((a, b) => a.y - b.y);
  const minGap = 27, maxY = m.t + ih, lastI = labelPos.length - 1;
  for (let i = 1; i <= lastI; i++)
    if (labelPos[i].y - labelPos[i - 1].y < minGap) labelPos[i].y = labelPos[i - 1].y + minGap;
  if (labelPos[lastI] && labelPos[lastI].y > maxY) {
    labelPos[lastI].y = maxY;
    for (let i = lastI - 1; i >= 0; i--)
      if (labelPos[i].y > labelPos[i + 1].y - minGap) labelPos[i].y = labelPos[i + 1].y - minGap;
  }
  labelPos.forEach((l) => {
    const g = el("g", { class: "dlabel", "data-area": l.area });
    g.appendChild(el("polyline", { fill: "none", stroke: l.c, "stroke-width": 1, opacity: .5,
      points: `${l.x + 3},${l.oy} ${l.x + 9},${l.y - 4} ${l.x + 14},${l.y - 4}` }));
    g.appendChild(el("text", { x: l.x + 18, y: l.y - 1, fill: l.c, "font-weight": "700", text: shortArea(l.area) }));
    g.appendChild(el("text", { x: l.x + 18, y: l.y + 12, fill: "#8a8d91", class: "num", "font-size": "10", text: fmtB(l.v) }));
    svg.appendChild(g);
  });
  svg.querySelectorAll("[data-area]").forEach((n) => {
    const a = n.getAttribute("data-area");
    n.addEventListener("mouseenter", () => trendFocus(svg, a));
    n.addEventListener("mouseleave", () => trendFocus(svg, null));
    if (n.tagName === "polyline") n.addEventListener("click", () => trendFocus(svg, a));
  });
  host.appendChild(svg);
  const chips = el("div", { class: "legend", style: "flex-direction:row;flex-wrap:wrap;gap:6px;margin-top:14px" });
  rows.forEach((r) => chips.appendChild(el("button", { class: "legend-row", type: "button",
    style: "width:auto;display:inline-flex;gap:7px;padding:7px 11px",
    onmouseenter: () => trendFocus(svg, r.area), onmouseleave: () => trendFocus(svg, null),
    onclick: () => trendFocus(svg, r.area) }, [
    el("span", { class: "dot", style: `background:${colorFor(r.area)}` }),
    el("span", { class: "lname", style: "max-width:none", text: shortArea(r.area) })])));
  host.appendChild(chips);
  const stems = [...new Set(DATA.by_area.map((r) => r.source_stem))];
  host.appendChild(el("div", { class: "chart-cite" }, ["Sources: ",
    ...stems.flatMap((s, i) => [i ? " · " : "", cite(s, DATA.by_area.find((r) => r.source_stem === s).page)])]));
}
function trendFocus(svg, area) {
  svg.classList.toggle("has-active", !!area);
  svg.querySelectorAll("[data-area]").forEach((n) =>
    n.classList.toggle("active", !!area && n.getAttribute("data-area") === area));
}

// ============================ FUNDING TAB ============================
function barList(items, accentColor) {
  const max = Math.max(...items.map((i) => i.millions));
  const list = el("div", { style: "display:flex;flex-direction:column;gap:11px" });
  items.forEach((it, idx) => {
    list.appendChild(el("div", {}, [
      el("div", { style: "display:flex;justify-content:space-between;font-size:13.5px;font-weight:600;margin-bottom:5px" }, [
        el("span", { text: it.label || it.source }), el("span", { class: "num", text: fmtB(it.millions) })]),
      el("div", { style: "background:#e9edf2;border-radius:6px;height:13px;overflow:hidden" }, [
        el("div", { style: `width:${(it.millions / max) * 100}%;height:100%;border-radius:6px;background:${idx === 0 ? "var(--brand)" : accentColor}` })]),
    ]));
  });
  return list;
}
function tabFunding(root) {
  const sec = el("section", { class: "wrap" });
  sec.appendChild(sectionHead("Where it comes from", "Funding sources",
    "The general fund (taxes the state can spend on anything) and the nongeneral fund (federal money, tuition, and other dedicated revenue)."));
  const grid = el("div", { class: "grid-2" });
  const gf = DATA.gf_resources_fy2026 || [], ngf = DATA.ngf_revenue || [];
  if (gf.length) grid.appendChild(el("div", { class: "panel" }, [
    el("h3", { class: "panel-title", text: "General fund · FY2026" }),
    el("div", { class: "panel-note" }, ["Where the general fund comes from. ", cite(gf[0].source_stem, gf[0].page)]),
    barList(gf, "var(--accent)"),
  ]));
  if (ngf.length) grid.appendChild(el("div", { class: "panel" }, [
    el("h3", { class: "panel-title", text: "Nongeneral fund · FY2024-2026" }),
    el("div", { class: "panel-note" }, ["Dedicated revenue ($104.4B), mostly federal grants. ", cite(ngf[0].source_stem, ngf[0].page)]),
    barList(ngf, "#8b5cf6"),
  ]));
  sec.appendChild(grid);
  root.appendChild(sec);
}

// ============================ NEXT YEAR TAB ============================
function tabNextYear(root) {
  const spend = DATA.totals.find((t) => t.biennium === "FY2026-2028" && t.kind === "GF spending");
  const res = DATA.totals.find((t) => t.biennium === "FY2026-2028" && t.kind === "GF resources");
  const rows = areaRows();
  const introTot = totalFor(rows, "introduced"), amendedTot = totalFor(rows, "amended");

  const kpis = el("div", { class: "kpis wrap" });
  if (spend) kpis.appendChild(kpiTile("Proposed GF spending", String(spend.billions), "B", "FY2026-2028 (HB 30)", false, cite(spend.source_stem, spend.page, { short: true })));
  if (res) kpis.appendChild(kpiTile("GF resources available", String(res.billions), "B", "FY2026-2028 (HB 30)", true, cite(res.source_stem, res.page, { short: true })));
  kpis.appendChild(kpiTile("Change vs current", "+" + fmtMoneyB(introTot - amendedTot), "B", "vs FY2024-2026 amended", true, null));
  root.appendChild(kpis);

  // by-area: FY26-28 introduced vs FY24-26 amended
  const sec = el("section", { class: "wrap" });
  sec.appendChild(sectionHead("", "Proposed budget by area",
    "How HB 30 (introduced January 2026) compares to the current amended budget, by area. Each row links to its source page."));
  const tbody = el("tbody");
  [...rows].sort((a, b) => b.introduced - a.introduced).forEach((r) => {
    const up = r.deltaNext >= 0;
    tbody.appendChild(el("tr", {}, [
      el("td", {}, [el("span", { class: "area-cell" }, [el("span", { class: "dot", style: `background:${colorFor(r.area)}` }), shortArea(r.area)])]),
      el("td", { class: "num", text: r.amended ? fmtB(r.amended) : "—" }),
      el("td", { class: "num big", text: r.introduced ? fmtB(r.introduced) : "—" }),
      el("td", { class: "num delta " + (up ? "up" : "down"), text: (up ? "▲ " : "▼ ") + fmtM(Math.abs(r.deltaNext)) }),
      el("td", {}, [r.srcNext ? cite(r.srcNext.source_stem, r.srcNext.page, { short: true }) : "—"]),
    ]));
  });
  const tfoot = el("tfoot", {}, [el("tr", {}, [
    el("td", { text: "Total general fund" }), el("td", { class: "num", text: fmtB(amendedTot) }),
    el("td", { class: "num", text: fmtB(introTot) }),
    el("td", { class: "num delta up", text: "▲ " + fmtM(introTot - amendedTot) }), el("td", {}, [""]),
  ])]);
  const thead = el("thead", {}, [el("tr", {}, ["Area", "Current (amended)", "Proposed (HB 30)", "Change", "Source"]
    .map((h) => el("th", { scope: "col", text: h })))]);
  const caption = el("caption", { class: "visually-hidden",
    text: "FY2026-2028 proposed general fund by secretarial area compared with the current amended budget, in billions of dollars." });
  sec.appendChild(el("div", { class: "panel" }, [el("div", { class: "table-scroll" },
    [el("table", { class: "budget nextyear-cols" }, [caption, thead, tbody, tfoot])])]));
  root.appendChild(sec);

  // key changes, grouped — each verbatim with a page citation
  const sec2 = el("section", { class: "wrap" });
  sec2.appendChild(sectionHead("", "Key changes in HB 30",
    "Substantive changes pulled from the 107-page committee overview of HB 30. Every line is verbatim and links to its page."));
  const grid = el("div", { class: "change-grid" });
  (DATA.next_year_changes || []).forEach((c) => {
    grid.appendChild(el("div", { class: "change-card" }, [
      el("div", { class: "change-top" }, [
        el("span", { class: "change-area", style: `--c:${colorFor(c.area === "Overall" ? "" : c.area)}`, text: c.area }),
        cite(c.source_stem, c.page, { short: true }),
      ]),
      el("div", { class: "change-headline", text: c.headline }),
      el("blockquote", { class: "change-quote", text: c.text }),
    ]));
  });
  sec2.appendChild(grid);
  root.appendChild(sec2);

  // next-year quotes (conf report policy items)
  const nyQuotes = DATA.quotes.filter((q) => ["Data centers", "Tax relief"].includes(q.topic));
  if (nyQuotes.length) {
    const sec3 = el("section", { class: "wrap" });
    sec3.appendChild(sectionHead("", "Tax and policy changes", ""));
    sec3.appendChild(quoteGrid(nyQuotes));
    root.appendChild(sec3);
  }
}

// ============================ QUOTES & SOURCES TAB ============================
function quoteGrid(quotes) {
  const grid = el("div", { class: "quote-grid" });
  quotes.forEach((q) => grid.appendChild(el("div", { class: "qcard" }, [
    el("span", { class: "topic", text: q.topic }),
    el("blockquote", { text: q.text }),
    q.principle ? el("div", { class: "principle", text: q.principle }) : null,
    el("div", { class: "cite-row" }, [cite(q.source_stem, q.page, { short: true }), el("span", { class: "src", text: q.doc_title })]),
  ])));
  return grid;
}
function tabSources(root) {
  const sec = el("section", { class: "wrap" });
  sec.appendChild(sectionHead("", "Quotes from the source documents",
    "Every quote is verbatim from the official document and links to the exact page."));
  sec.appendChild(quoteGrid(DATA.quotes));
  root.appendChild(sec);

  const sec2 = el("section", { class: "wrap" });
  sec2.appendChild(sectionHead("", "Source documents", ""));
  if (VALIDATION) sec2.appendChild(el("p", { class: "verified-note" }, [
    el("span", { class: "vcheck", "aria-hidden": "true", text: "✓ " }),
    `${VALIDATION.passed}/${VALIDATION.total} data points verified against source (checked ${VALIDATION.validated_on}). Run scripts/validate.py to re-check.`,
  ]));
  const grid = el("div", { class: "src-grid" });
  DATA.sources.forEach((s) => grid.appendChild(el("div", { class: "src-card" }, [
    el("div", { class: "badge", text: s.biennium + " · " + s.stage }),
    el("h3", { text: s.title }),
    el("div", { class: "meta", text: `${s.publisher} · ${s.page_count} pp · as of ${s.as_of}` }),
    el("div", { style: "margin-top:10px" }, [el("a", { href: s.url, target: "_blank", rel: "noopener", text: "Open document ↗" })]),
  ])));
  sec2.appendChild(grid);
  root.appendChild(sec2);
}
