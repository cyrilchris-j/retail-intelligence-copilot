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

function badge(priority) {
  const p = (priority || "low").toLowerCase();
  return `<span class="badge ${p}">${p}</span>`;
}

function renderAttention(items) {
  if (!items?.length) return "<p>No attention items matched current thresholds.</p>";
  return items.map((item) => {
    const title = [item.product_name, item.store_name].filter(Boolean).join(" · ") || item.issue_type;
    const metrics = item.metrics || {};
    const metricLine = Object.entries(metrics)
      .filter(([k]) => k !== "windows")
      .slice(0, 5)
      .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`)
      .join(" · ");
    return `<article class="issue">
      <div class="issue-top"><strong>${title}</strong>${badge(item.priority)}</div>
      <div class="reason">${item.issue_type.replaceAll("_", " ")} — ${item.reason}</div>
      <div class="metrics">${metricLine}</div>
      <div class="action"><strong>Consider:</strong> ${item.recommended_action}</div>
    </article>`;
  }).join("");
}

function table(headers, rows) {
  if (!rows.length) return "<p>None at current thresholds.</p>";
  return `<table><thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
    <tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}

function renderCopilot(data) {
  const findings = (data.findings || []).map((f) => {
    if (!f || typeof f !== "object") return `<li>${f}</li>`;
    if (f.options) return `<li>Options: ${f.options.join(", ")}</li>`;
    return `<li>${f.reason || ""}</li>`;
  }).join("");
  const evidence = (data.evidence || []).map((e) =>
    `<li><code>${e.evidence_id}</code> ${e.metric}=${e.value} ${e.product_id || ""} ${e.store_id || ""} ${e.period || ""}</li>`
  ).join("");
  const assumptions = (data.assumptions || []).map((a) => `<li>${a}</li>`).join("");
  const aiNote = data.ai_available ? "" : `<p class="warn">${data.answer.includes("unavailable") ? "" : "AI explanation is currently unavailable. Showing deterministic analytics."}</p>`;
  return `${aiNote}
    <div class="answer"><strong>${(data.status || "").replaceAll("_", " ")}</strong>
      <p>${data.answer}</p>
      ${data.recommendation ? `<p><strong>Recommended action:</strong> ${data.recommendation}</p>` : ""}
      ${data.missing ? `<p class="warn">${data.missing}</p>` : ""}
    </div>
    <details open><summary>Findings</summary><ul>${findings || "<li>None</li>"}</ul></details>
    <details><summary>Evidence</summary><ul>${evidence || "<li>None</li>"}</ul></details>
    <details><summary>Assumptions</summary><ul>${assumptions || "<li>None</li>"}</ul></details>
    <details><summary>Retrieved policies</summary><ul>${(data.retrieved_policies || []).map((p) => `<li><code>${p.chunk_id}</code> ${p.source}</li>`).join("") || "<li>None</li>"}</ul></details>`;
}

async function loadDashboard() {
  const [health, dash] = await Promise.all([getJson("/api/health"), getJson("/api/dashboard")]);
  document.getElementById("health-pill").textContent = health.gemini_configured ? "Gemini configured" : "Deterministic mode";
  document.getElementById("biz-date").textContent = dash.business_date;
  document.getElementById("data-range").textContent = `${dash.data_range.min_date} → ${dash.data_range.max_date}`;
  const s = dash.summary;
  document.getElementById("kpis").innerHTML = [
    kpi("Month units", num(s.units_sold), `MoM ${pct(s.month_over_month_units_pct)}`),
    kpi("Month revenue", inr(s.revenue), `MoM ${pct(s.month_over_month_revenue_pct)}`),
    kpi("Lifetime units", num(s.lifetime_units), "All 90-day history"),
    kpi("Inventory units", num(s.inventory_units), "Current on-hand"),
  ].join("");
  document.getElementById("attention-list").innerHTML = renderAttention(dash.attention);
  document.getElementById("stockouts").innerHTML = table(
    ["Product", "Store", "Stock", "ADS", "Coverage", "Risk"],
    (dash.inventory_risks.stockouts || []).map((r) => [r.product_name, r.store_name, r.current_stock, r.average_daily_sales, r.coverage_days ?? "undef", r.risk])
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
  box.innerHTML = "<p>Running analytics…</p>";
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
    ask(btn.dataset.q);
  });
});

loadDashboard().catch((err) => {
  document.getElementById("attention-list").innerHTML = `<p class="warn">${err.message}</p>`;
});
