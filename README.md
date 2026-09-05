TRACK_ID=PS03

# Retail Intelligence Copilot

> An evidence-grounded AI decision-support system that helps retail managers understand sales and inventory, identify what needs attention, and make faster data-backed decisions.

## Problem Statement

**PS03 — Retail: Sales and Inventory Copilot**

Store managers work with rich sales, product, store, and inventory data, but important decisions are often buried across reports and stock records.

Retail Intelligence Copilot brings this information into one operational workspace and helps managers answer:

- What products are likely to run out?
- Which products are overstocked?
- How did a product perform during a comparable period?
- Which store needs attention?
- Which sales spikes or drops are worth investigating?
- What should be prioritized today?

The system works from the application's own retail data and does not rely on unsupported AI-generated business facts.

## Solution

Retail Intelligence Copilot combines:

- Deterministic retail analytics
- Local SQLite data
- Local policy retrieval
- Gemini-powered natural-language explanation
- Evidence-backed recommendations
- Explicit uncertainty handling

The core design separates **business facts and calculations** from **LLM reasoning**.

Python calculates the actual business metrics and identifies issues. Gemini receives verified context and explains the findings in a manager-friendly format.

## Key Features

### Sales Intelligence

- Product-level sales analysis
- Comparable-period sales analysis
- Sales growth and decline detection
- Sales spike detection
- Sales drop detection
- Store-level sales performance
- Historical sales comparison

### Inventory Intelligence

- Current inventory monitoring
- Low-stock identification
- Stock-out risk detection
- Replenishment review
- Overstock detection
- Inventory coverage calculation
- Reorder-level comparison

### Attention Management

The system identifies issues requiring manager attention and prioritizes them using deterministic business rules.

Attention signals include:

- Critical stock-out risk
- High stock-out risk
- Medium stock-out risk
- Replenishment review
- Overstock
- Sales decline
- Sales spike
- Store underperformance

### Manager Copilot

Managers can ask questions in natural language such as:

    What products are likely to run out?

    Which products are overstocked?

    How did Wireless Mouse perform this month?

    Why did sales drop for USB-C Hub?

    Which store needs attention?

    What should I prioritize today?

    Compare Chennai Central with Madurai.

## Evidence-First Answers

The system does not treat Gemini as the source of truth for retail metrics.

For example:

    Product: Wireless Mouse
    Current Stock: 12 units
    Average Daily Sales: 7.43 units
    Inventory Coverage: 1.6 days
    Reorder Level: 30 units
    Status: Critical Stock-Out Risk

The application can then provide a recommendation such as:

    Review replenishment for Wireless Mouse at Bengaluru MG Road.

Supporting figures and evidence remain visible so the manager can understand why the recommendation was made.

## Deterministic Logic vs Gemini

### Deterministic Python Logic

Python is responsible for:

- Sales calculations
- Revenue calculations
- Comparable-period calculations
- Average daily sales
- Inventory coverage
- Stock-out classification
- Replenishment review
- Overstock detection
- Sales trend detection
- Store performance
- Priority scoring
- Data validation

### Gemini

Gemini is responsible for:

- Natural-language understanding
- Explanation of verified findings
- Interpretation of retrieved context
- Manager-friendly summaries
- Recommendation wording

Gemini is not allowed to invent:

- Sales figures
- Inventory values
- Products
- Stores
- Dates
- Metrics
- Business facts

## Grounded Retrieval

The project uses a local retrieval pipeline for business policies and supporting operational guidance.

    Business Rules
          |
          v
    Document Chunking
          |
          v
    Gemini Embeddings
    gemini-embedding-001
          |
          v
    Local Index
          |
          v
    Similarity Search
          |
          v
    Relevant Context
          |
          v
        Gemini
          |
          v
    Grounded Explanation

Relevant policy areas include:

- Stock-out policy
- Overstock policy
- Inventory policy
- Sales analysis guidance
- Store operations guidance
- Recommendation guidance

No hosted vector database or third-party RAG service is required.

## Stock-Out Rules

The application uses centralized stock-out thresholds:

    Coverage <= 2 days
    Critical

    Coverage > 2 and <= 5 days
    High

    Coverage > 5 and <= 7 days
    Medium

    Coverage > 7 days
    Not a stock-out risk

When sales velocity is zero and coverage is undefined, the application does not classify the item as a normal stock-out.

If inventory is at or below the reorder level while coverage is above the stock-out threshold, the system treats it as a separate replenishment-review signal.

## Sales Comparison

The dashboard uses equal-length comparison windows instead of comparing an incomplete current month against a full previous month.

For example:

    Current period:
    September 1–4

    Comparison period:
    August 1–4

This provides a fair comparison for:

- Units
- Revenue

If the comparison baseline is zero or insufficient, the system does not fabricate a percentage.

## Priority Engine

The system deterministically ranks important issues before Gemini is used for explanation.

Priority inputs can include:

- Stock-out severity
- Inventory coverage
- Sales decline
- Sales spike
- Revenue impact
- Store performance
- Other configured attention signals

Example:

    Priority 1
    Wireless Mouse — Bengaluru MG Road
    1.6 days of inventory coverage
    12 units remaining

    Priority 2
    USB-C Hub
    Sales down 45.3%

    Priority 3
    Madurai
    41.9% below store average

Python determines the priority.

Gemini explains the priority using verified evidence.

## No-Data and Uncertainty Handling

The system does not invent information when the available data cannot answer a question.

Example:

    User:
    How are our Europe stores performing?

    System:
    The available dataset does not contain Europe store data,
    so this question cannot be answered from the available
    information.

The same principle applies to:

- Unknown products
- Unknown stores
- Unsupported locations
- Metrics not present in the dataset
- Missing historical data
- Insufficient comparison periods

## Gemini Failure Handling

When Gemini is unavailable:

- Deterministic analytics remain usable
- Actual business figures remain available
- Evidence remains available
- Deterministic recommendations remain available where possible
- The interface clearly indicates that AI explanation is unavailable

The application never falsely claims that Gemini generated a response.

## Data

No dataset is provided for PS03.

The application therefore uses its own generated retail data.

The dataset contains:

- Multiple stores
- Multiple products
- Daily sales
- Historical sales
- Current inventory
- Reorder levels
- Stock thresholds
- Normal sales patterns
- Sales spikes
- Sales drops
- Low-stock scenarios
- Overstock scenarios
- Store performance differences
- Difficult and no-data scenarios

The generated data is deterministic and designed for reproducible demonstrations.

## Database

The application uses a local SQLite database.

Core tables:

    stores
    products
    sales
    inventory

### Stores

    store_id
    store_name
    location

### Products

    product_id
    product_name
    category
    price
    reorder_level
    target_stock

### Sales

    sale_id
    sale_date
    store_id
    product_id
    quantity
    revenue

### Inventory

    inventory_id
    store_id
    product_id
    current_stock
    updated_at

No hosted database service is required.

## Technology Stack

- Python 3.11
- FastAPI
- Uvicorn
- SQLite
- Pandas
- NumPy
- python-dotenv
- Google GenAI SDK
- Gemini API
- gemini-embedding-001
- Local retrieval
- HTML
- CSS
- JavaScript

The frontend is served by the Python application.

## External API Policy

Gemini is the only external API used by the project.

The application does not depend on:

- OpenAI API
- Anthropic API
- Groq API
- Hosted vector databases
- Third-party RAG services
- Third-party memory services
- Other external APIs

Application data, database operations, deterministic analytics and retrieval remain local.

## Environment Configuration

Required environment variable:

    GEMINI_API_KEY

Example:

    GEMINI_API_KEY=your_gemini_api_key

The actual API key must never be committed to the repository.

Copy `.env.example` to `.env` and provide the key locally.

## Project Structure

    retail-intelligence-copilot/
    ├── app.py
    ├── requirements.txt
    ├── README.md
    ├── .env.example
    ├── .gitignore
    │
    ├── src/
    │   ├── analytics/
    │   │   ├── sales.py
    │   │   ├── inventory.py
    │   │   └── trends.py
    │   ├── retrieval/
    │   │   └── retriever.py
    │   ├── llm/
    │   │   ├── gemini.py
    │   │   └── prompts.py
    │   ├── services/
    │   │   ├── copilot.py
    │   │   └── recommendations.py
    │   └── models/
    │       └── schemas.py
    │
    ├── data/
    │   ├── retail.db
    │   ├── stores.csv
    │   ├── products.csv
    │   ├── sales.csv
    │   ├── inventory.csv
    │   └── business_rules/
    │
    ├── index/
    │   ├── embeddings.npy
    │   └── chunks.json
    │
    ├── frontend/
    │   └── dist/
    │
    ├── scripts/
    │   ├── generate_data.py
    │   ├── build_index.py
    │   └── validate.py
    │
    └── tests/
        ├── test_analytics.py
        ├── test_copilot.py
        ├── test_gemini.py
        └── test_retrieval.py

## Installation

The project targets Python 3.11.

    python3.11 -m venv .venv

    source .venv/bin/activate

    pip install -r requirements.txt

## Run

From the repository root:

    python app.py

The complete application is served at:

    http://localhost:8000

No second terminal is required.

No separate frontend build command is required during evaluation.

## Evaluation Compatibility

The project is designed around the NexusTiq24 evaluation requirements.

    Python:
    3.11

    Installation:
    pip install -r requirements.txt

    Run:
    python app.py

    Port:
    8000

The application is designed to:

- Start from a clean clone
- Serve the complete application on port 8000
- Use the committed local data
- Load the committed retrieval index
- Use Gemini only when required
- Handle incomplete input
- Handle ambiguous input
- Handle unsupported questions
- Handle model failures gracefully
- Avoid unnecessary startup-time indexing
- Keep normal requests within the required request window

## Performance Strategy

To keep the application responsive:

- Generated data is committed
- SQLite is local
- Retrieval is local
- Embeddings are precomputed
- The retrieval index is committed
- The application does not rebuild the complete embedding index at startup
- Gemini receives only relevant structured context
- Database queries are targeted
- Deterministic analytics are lightweight

## Error Handling

The application handles:

- Empty questions
- Invalid input
- Unknown products
- Unknown stores
- Missing data
- Unsupported locations
- Unsupported metrics
- Zero sales velocity
- Zero comparison baseline
- Insufficient historical data
- Retrieval failures
- Database failures
- Gemini API failures
- Invalid Gemini responses

The system is designed to fail gracefully instead of exposing raw exceptions.

## Security

Sensitive credentials are never stored in source code.

Never commit:

- API keys
- `.env`
- Secrets
- Virtual environments
- Model weights

Only `.env.example` is committed as the environment template.

## Testing

The project includes tests covering:

- Inventory coverage
- Stock-out thresholds
- Replenishment review
- Overstock detection
- Sales spikes
- Sales drops
- Equal-window MTD comparison
- Priority ranking
- Policy retrieval
- Gemini fallback
- Copilot behaviour
- No-data handling
- Evidence generation

Run the test suite:

    pytest tests/

Run application validation:

    python scripts/validate.py

## Test Scenarios

### Normal Case

    What products are likely to run out?

Expected:

- Genuine stock-out risks
- Current stock
- Average daily sales
- Coverage
- Severity
- Supporting evidence
- Recommendation

### Difficult Case

    What should I prioritize today?

Expected:

- Multiple competing issues
- Deterministic priority ranking
- Highest-priority issue
- Supporting metrics
- Evidence
- Recommendation
- Relevant policy

### No-Data Case

    How are our Europe stores performing?

Expected:

    The available dataset does not contain Europe store data,
    so this question cannot be answered from the available
    information.

### Trend Case

    Why did sales drop for USB-C Hub?

Expected:

- Recent sales
- Comparable baseline
- Change percentage
- Evidence
- Explanation based only on available data

## Design Principles

### Deterministic First

Business facts and calculations are generated using deterministic Python logic.

### Grounded AI

Gemini responses are based on verified application data and retrieved context.

### Evidence Over Claims

Important answers expose the business figures supporting the conclusion.

### Honest Uncertainty

The system explicitly communicates when information is unavailable.

### Explainable Recommendations

Recommendations show the reasoning, relevant data and assumptions.

### Human Decision Support

The system recommends actions but does not automatically execute business decisions.

## Demo

The demonstration focuses on three scenarios:

### 1. Normal Case

    What products are likely to run out?

The system identifies genuine stock-out risks and shows the supporting figures.

### 2. Difficult Case

    What should I prioritize today?

The system compares multiple issues and produces a ranked, evidence-backed priority list.

### 3. No-Data Case

    How are our Europe stores performing?

The system refuses to invent information and clearly communicates that the required data is unavailable.

## Git Development

Development is committed progressively throughout the project.

The repository history reflects:

    Initial project setup
    Database and data model
    Generated retail data
    Sales analytics
    Inventory analytics
    Attention detection
    FastAPI endpoints
    Dashboard
    Gemini integration
    Local retrieval
    Copilot
    Evidence
    Recommendations
    Edge cases
    UI improvements
    Final validation

Example:

    git add .
    git commit -m "Improve grounded copilot responses"

## Submission

GitHub Repository:

https://github.com/cyrilchris-j/retail-intelligence-copilot

Demo Video:

https://youtu.be/sRJMTo7nJ5s?si=u0bUNxJ3P1Trvp_Q

## Hackathon

**NexusTiq24**

**Track ID:** PS03

**Problem Statement:** Retail — Sales and Inventory Copilot

**Backend:** Python

**Entry Point:** `app.py`

**Application Port:** `8000`
