TRACK_ID=PS03

Problem Statement: PS03 — Retail: Sales and Inventory Copilot

# Retail Intelligence Copilot

Decision-support copilot for a small multi-store retailer. Store managers ask plain-language questions about stock-outs, overstock, product performance, and which issues to prioritize. Numbers come from SQLite and deterministic analytics. Gemini only explains evidence that the application already computed.

## Problem statement

PS03 — Retail: Sales and Inventory Copilot.

A manager running several stores needs to know what is running out, what is overstocked, how a product did this month, which store needs attention, which sales spikes or drops are worth investigating, and what to prioritize today.

## Solution

The application loads a committed SQLite retail database, computes inventory coverage and sales-change metrics with documented formulas, ranks attention items, and optionally asks Gemini to write a manager-facing explanation from that structured context. Local retrieval supplies inventory and recommendation policies. The system does not place orders or change records.

## Core features

- Dashboard: month sales, revenue, units, on-hand inventory, attention list, stock-out risk, overstock, spikes/drops, store performance, top products
- Natural-language copilot with intent routing (stock-out, overstock, performance, comparison, priority, no-data)
- Transparent coverage, overstock, spike/drop, and priority formulas (single source of truth in `src/config.py`)
- Month-over-month compares equal-length windows: September MTD vs August 1–4, never a partial month against a full month
- "What should I prioritize today?" returns a deterministic Priority 1/2/3 ranking; Gemini explains, never re-ranks
- Local policy retrieval (committed embeddings) with stable policy ids visible in the UI
- Evidence identifiers on important answers, rendered as manager-readable cards
- Honest refusal when the dataset cannot answer (for example Europe/Tokyo stores, unknown products, unsupported metrics)
- Truthful Gemini status: the header says "Connected" only after a real request succeeds; otherwise "Unavailable" or "Not Configured"
- Gemini fallback: analytics still run if the API key is missing or the model fails

## Architecture

User → HTML dashboard → FastAPI → services → SQLite + analytics engine → optional local policy retrieval → Gemini explanation → answer + evidence + recommendation

Separated layers: configuration, data access, analytics, retrieval, Gemini, API routes, frontend, validation.

### Deterministic vs AI

| Responsibility | Owner |
| --- | --- |
| Sales, inventory, coverage, spikes, drops, priority scores | Python analytics |
| Entity lookup and no-data checks | Copilot service |
| Policy text for recommendations | Local retrieval |
| Wording of explanations | Gemini |
| Business figures | Never Gemini |

### Grounding strategy

Quantitative facts are SQL + formulas. Gemini receives structured facts, evidence ids, and policy chunks, and must not invent numbers. Invalid Gemini JSON is retried once, then replaced with a deterministic narrative.

## Data

Seeded synthetic India retail network (seed 42), business date **2026-09-04**, 90 days of sales.

| Entity | Count / notes |
| --- | --- |
| Stores | 5: Chennai Central, Coimbatore, Bengaluru MG Road, Hyderabad Banjara, Madurai |
| Products | 40 SKUs across Electronics, Office, Home, Accessories, Stationery |
| Sales | Daily units and revenue by store and product |
| Inventory | Current on-hand by store and product |

Seeded demo situations include: Wireless Mouse low coverage; Office Chair / Storage Box overstock; Mechanical Keyboard spike; USB-C Hub drop; Madurai underperformance; similar names (Wireless Mouse / Pro / Mini, Mechanical vs Membrane Keyboard).

## Database

SQLite file `data/retail.db` with `stores`, `products`, `sales`, `inventory`, foreign keys, and indexes on sales date / store / product.

## Technology stack

Python 3.11, FastAPI, Uvicorn, SQLite, Pandas, NumPy, python-dotenv, google-genai (Gemini only). Frontend is static HTML/CSS/JS served by Python. No hosted vector database.

## Environment variable

Copy `.env.example` to `.env`:

```
GEMINI_API_KEY=
```

Never commit `.env`. Never hard-code keys. Embeddings, when rebuilt, use `gemini-embedding-001`.

## Project structure

```
app.py
requirements.txt
README.md
src/           config, database, analytics, retrieval, llm, services, utils
data/          retail.db, CSVs, business_rules/
index/         embeddings.npy, chunks.json
frontend/dist/ dashboard assets
scripts/       generate_data.py, build_index.py, validate.py
```

## Installation

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional: `export GEMINI_API_KEY=...` or a local `.env`.

## Run

```bash
python app.py
```

Opens `http://localhost:8000`. No second terminal, no npm build, no manual database setup.

Regenerate data or the policy index only when developing:

```bash
python scripts/generate_data.py
python scripts/build_index.py
python scripts/validate.py
```

## Evaluation compatibility

- Entry point: `python app.py` on port 8000
- Dependencies: `pip install -r requirements.txt`
- First README line: `TRACK_ID=PS03`
- Gemini is the only external API
- Dataset and index are committed; startup does not rebuild embeddings

## Performance

Startup loads SQLite and the local index only. Gemini is called on copilot questions when a key is present. Dashboard analytics use grouped SQL, not per-row scans of the full history.

## Error handling

Empty questions, unknown products/stores, unsupported geography or metrics, zero velocity, zero baseline, Gemini timeout/invalid JSON, retrieval failure, and database errors return structured responses instead of crashing.

## Security

API keys from the environment only. No arbitrary SQL from the user. The copilot never executes operational actions.

## Git development strategy

Incremental commits from skeleton → schema/data → analytics → API → dashboard → Gemini/retrieval → copilot/evidence → edge cases → polish.

## Test scenarios

`python scripts/validate.py` checks coverage math, exact stock-out thresholds (including the >7-day non-stock-out rule), overstock, equal-window MTD, percent-change notes, ranked priorities, policy retrieval, no-data cases (Europe, Tokyo, profit, employees), Gemini fallback, and response parsing. A pytest suite lives in `tests/` (`pytest tests/`).

## Demo plan

1. Open the dashboard and read **Needs Attention Today**.
2. Ask: `What products are likely to run out?` — stock, ADS, coverage, risk, evidence.
3. Ask: `What should I prioritize today?` — mixed issue types and ranking.
4. Ask: `How are our Europe stores performing?` — refusal, no invented stores.

## Submission

- Track: PS03
- Team: _(fill in)_
- Repository: _(fill in)_
