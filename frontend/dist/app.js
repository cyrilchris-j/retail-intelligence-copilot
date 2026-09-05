const inr = (n) => n == null ? "—" : "₹" + Math.round(n).toLocaleString("en-IN");
const num = (n, d = 0) => n == null || Number.isNaN(n) ? "—" : Number(n).toLocaleString("en-IN", { maximumFractionDigits: d, minimumFractionDigits: d });
const pct = (n) => n == null ? "n/a" : `${n > 0 ? "+" : ""}${n.toFixed(1)}%`;

async function getJson(url, options) {
  const res = await fetch(url, options);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || data.message || "Request failed");
  return data;
}

function kpi(label, value, note) {
  return `<article class="kpi"><span>${label}</span><strong>${value}</strong><em>${note || ""}</em></article>`;
}

function badge(priority, cls) {
  const p = (priority || "low").toLowerCase();
  return `<span class="badge ${cls || p}">${priority || p}</span>`;
}

function sevOf(priority) {
  const p = (priority || "low").toLowerCase();
  return ["high", "critical"].includes(p) ? "high" : p;
}

function renderAttention(items) {
  if (!items?.length) return "<p class=\"note\">No attention items matched current thresholds.</p>";
  return items.map((item) => {
    const title = [item.product_name, item.store_name].filter(Boolean).join(" · ") || item.issue_type;
    const metrics = item.metrics || {};
    const metricLine = Object.entries(metrics)
      .filter(([k]) => k !== "windows")
      .slice(0, 5)
      .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`)
      .join(" · ");
    const rankBadge = item.rank ? badge(item.rank, "priority") : "";
    const prioBadge = badge(item.priority);
    return `<article class="issue" data-sev="${sevOf(item.priority)}">
      <div class="issue-top"><strong>${title}</strong><span style="display:flex;gap:6px;">${rankBadge}${prioBadge}</span></div>
      <div class="reason">${item.issue_type.replaceAll("_", " ")} — ${item.reason}</div>
      <div class="metrics">${metricLine}</div>
      <div class="action"><strong>Consider:</strong> ${item.recommended_action}</div>
    </article>`;
  }).join("");
}

function table(headers, rows) {
  if (!rows.length) return "<p class=\"note\">None at current thresholds.</p>";
  return `<table><thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
    <tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}

const EVIDENCE_GROUP_TITLES = {
  inventory: "Inventory Evidence",
  sales: "Sales Evidence",
  policy: "Policy Evidence",
  product: "Product Evidence",
  store: "Store Evidence",
  rule: "Rule Evidence",
  calc: "Calculated Metrics",
};

function renderEvidenceList(evidence) {
  if (!evidence?.length) return "<li>None</li>";
  const groups = {};
  for (const e of evidence) {
    const key = e.group || e.type || "evidence";
    (groups[key] = groups[key] || []).push(e);
  }
  return Object.entries(groups).map(([group, items]) => {
    const title = EVIDENCE_GROUP_TITLES[group] || group.replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase());
    const rows = items.map((e) => {
      const context = [e.product_name, e.store_name].filter(Boolean).join(" · ");
      const reference = e.policy_id || e.evidence_id;
      return `<li style="margin-bottom: 8px;">
        ${context ? `<div style="opacity: 0.85;">${context}</div>` : ""}
        <div><strong>${e.label || e.metric.replaceAll("_", " ")}:</strong> ${e.display_value ?? e.value}</div>
        <em style="font-size: 0.85em; opacity: 0.7;">Reference: ${reference}</em>
      </li>`;
    }).join("");
    return `<div class="evidence-card"><strong>${title}</strong></div><ul style="margin: 4px 0 10px; padding-left: 18px;">${rows}</ul>`;
  }).join("");
}

function renderFindings(findings) {
  if (!findings?.length) return "<li>None</li>";
  return findings.map((f) => {
    if (!f || typeof f !== "object") return `<li>${f}</li>`;
    if (f.options) return `<li>Options: ${f.options.join(", ")}</li>`;
    const rankBadge = f.rank ? badge(f.rank, "priority") : "";
    const typeBadge = f.issue_type ? `<span class="badge ${(f.priority || "low").toLowerCase()}">${f.issue_type.replaceAll("_", " ")}</span>` : "";
    return `<li style="margin-bottom: 8px;">${rankBadge} ${typeBadge} ${f.reason || ""}</li>`;
  }).join("");
}

function renderCopilot(data) {
  const aiNote = (data.ai_available ?? data.ai_generated) ? "" : `<p class="warn">AI explanation is temporarily unavailable. Deterministic analytics are still available.</p>`;
  const policies = (data.retrieved_policies || []).map((p) =>
    `<li><strong>${p.title || p.source}</strong>${p.policy_id ? ` <em style="font-size: 0.85em; opacity: 0.7;">(${p.policy_id})</em>` : ""}<br/>${p.text}</li>`
  ).join("");
  return `${aiNote}
    <div class="answer"><strong class="status-label">${(data.status || "").replaceAll("_", " ")}</strong>
      <p>${data.answer}</p>
      ${data.recommendation ? `<p><strong>Recommended action:</strong> ${data.recommendation}</p>` : ""}
      ${data.missing ? `<p class="warn">${data.missing}</p>` : ""}
    </div>
    <details open><summary>Findings</summary><ul>${renderFindings(data.findings)}</ul></details>
    <details open><summary>Retrieved policies</summary><ul>${policies || "<li>No specific policy retrieved</li>"}</ul></details>
    <details><summary>Evidence</summary><ul>${renderEvidenceList(data.evidence)}</ul></details>
    <details><summary>Assumptions</summary><ul>${(data.assumptions || []).map((a) => `<li>${a}</li>`).join("") || "<li>None</li>"}</ul></details>`;
}

function setHealthPill(health) {
  const status = health.gemini_status || (health.gemini_configured ? "connected" : "unavailable");
  const pill = document.getElementById("health-pill");
  if (status === "connected") {
    pill.textContent = "Gemini Connected";
    pill.className = "pill connected";
  } else if (status === "not_configured") {
    pill.textContent = "Gemini Not Configured";
    pill.className = "pill not-configured";
  } else {
    pill.textContent = "Gemini Unavailable";
    pill.className = "pill unavailable";
  }
}

const PAGE_META = {
  overview: ["Dashboard", "Overview"],
  attention: ["Dashboard", "Needs Attention"],
  copilot: ["Copilot", "Manager Copilot"],
  inventory: ["Operations", "Inventory Health"],
  insights: ["Analytics", "Sales Insights"],
  products: ["Analytics", "Top Products"],
  assumptions: ["Methodology", "Scoring Assumptions"],
};

function setupNav() {
  const links = document.querySelectorAll(".nav-link");
  const sections = Array.from(links).map((l) => document.getElementById(l.dataset.target)).filter(Boolean);
  const crumbs = document.getElementById("page-crumb");
  const title = document.getElementById("page-title");

  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const id = entry.target.id;
        links.forEach((l) => l.classList.toggle("active", l.dataset.target === id));
        const meta = PAGE_META[id];
        if (meta) {
          crumbs.textContent = meta[0];
          title.textContent = meta[1];
        }
      }
    },
    { rootMargin: "-25% 0px -65% 0px", threshold: 0 }
  );
  sections.forEach((s) => observer.observe(s));
}

function setupMobileMenu() {
  const btn = document.getElementById("menu-btn");
  const sidebar = document.getElementById("sidebar");
  const scrim = document.getElementById("sidebar-scrim");
  if (!btn || !sidebar || !scrim) return;
  const close = () => {
    sidebar.classList.remove("open");
    scrim.classList.remove("show");
  };
  btn.addEventListener("click", () => {
    sidebar.classList.toggle("open");
    scrim.classList.toggle("show");
  });
  scrim.addEventListener("click", close);
  sidebar.querySelectorAll(".nav-link").forEach((l) => l.addEventListener("click", close));
}

async function loadDashboard() {
  const [health, dash] = await Promise.all([getJson("/api/health"), getJson("/api/dashboard")]);
  setHealthPill(health);
  document.getElementById("biz-date").textContent = dash.business_date;
  const bizTop = document.getElementById("biz-date-top");
  if (bizTop) bizTop.textContent = dash.business_date;
  document.getElementById("data-refresh").textContent = dash.business_date + " 00:00:00 UTC";
  document.getElementById("data-range").textContent = `${dash.data_range.min_date} → ${dash.data_range.max_date}`;
  const s = dash.summary;
  const labels = s.month_labels || {};
  const momLabel = labels.comparison_label || "MoM";
  const unitsNote = s.month_over_month_units_note ? `<span style="color: var(--amber);">${s.month_over_month_units_note}</span>` : pct(s.month_over_month_units_pct);
  const revenueNote = s.month_over_month_revenue_note ? `<span style="color: var(--amber);">${s.month_over_month_revenue_note}</span>` : pct(s.month_over_month_revenue_pct);
  document.getElementById("kpis").innerHTML = [
    kpi("Month units", num(s.units_sold), `${momLabel}: ${unitsNote}`),
    kpi("Month revenue", inr(s.revenue), `${momLabel}: ${revenueNote}`),
    kpi("Lifetime units", num(s.lifetime_units), "All 90-day history"),
    kpi("Inventory units", num(s.inventory_units), "Current on-hand"),
  ].join("");
  const attention = dash.attention || [];
  const countEl = document.getElementById("attention-count");
  if (countEl) countEl.textContent = `${attention.length} ${attention.length === 1 ? "item" : "items"}`;
  document.getElementById("attention-list").innerHTML = renderAttention(attention);
  const rr = dash.inventory_risks.replenishment_review_count;
  document.getElementById("replenish-note").innerHTML = rr
    ? `<p class="note">${rr} item(s) are below reorder level with coverage above 7 days — flagged for replenishment review, not stock-out risk.</p>`
    : "";
  document.getElementById("stockouts").innerHTML = table(
    ["Product", "Store", "Stock", "ADS", "Coverage", "Risk"],
    (dash.inventory_risks.stockouts || []).map((r) => [r.product_name, r.store_name, r.current_stock, r.average_daily_sales, r.coverage_days ?? "undef", r.risk + (r.below_reorder ? " · below reorder" : "")])
  );
  document.getElementById("overstock").innerHTML = table(
    ["Product", "Store", "Stock", "Target", "Coverage"],
    (dash.inventory_risks.overstock || []).map((r) => [r.product_name, r.store_name, r.current_stock, r.target_stock, r.coverage_days ?? "undef"])
  );
  document.getElementById("trends").innerHTML = table(
    ["Product", "Change", "Recent", "Baseline"],
    (dash.sales_trends || []).map((r) => [r.product_name, pct(r.change_pct), r.recent_units, r.baseline_units])
  );
  document.getElementById("stores").innerHTML = table(
    ["Store", "Units", "Revenue", "vs avg", "Flag"],
    (dash.stores || []).map((r) => [r.store_name, r.units, inr(r.revenue), pct(r.vs_store_average_pct), r.underperforming ? "Needs attention" : "On track"])
  );
  document.getElementById("products").innerHTML = table(
    ["Product", "Units", "Revenue"],
    (dash.top_products || []).map((r) => [r.product_name, r.units, inr(r.revenue)])
  );
  document.getElementById("assumptions").innerHTML = (dash.assumptions || []).map((a) => `<li>${a}</li>`).join("");
}

async function ask(question) {
  const box = document.getElementById("copilot-result");
  box.innerHTML = "<p class=\"note\">Running analytics…</p>";
  try {
    const data = await getJson("/api/copilot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    box.innerHTML = renderCopilot(data);
  } catch (err) {
    box.innerHTML = `<p class="warn">${err.message}</p>`;
  }
}

document.getElementById("copilot-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const q = document.getElementById("question").value.trim();
  if (q) ask(q);
});
document.querySelectorAll(".chips button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.getElementById("question").value = btn.dataset.q;
  });
});

setupNav();
setupMobileMenu();
loadDashboard().catch((err) => {
  document.getElementById("attention-list").innerHTML = `<p class="warn">${err.message}</p>`;
});