TRACK_ID=PS03

# Retail Intelligence Copilot

AI-powered Sales and Inventory Copilot for small retail operations.

## Problem Statement

**PS03 — Retail: Sales and Inventory Copilot**

Retail managers have sales reports, product information, store information, and inventory data, but important insights are often buried across multiple records.

Retail Intelligence Copilot brings these data sources together and helps managers understand what requires attention, why it matters, and what action can be taken.

## Solution

The system combines deterministic retail analytics with Gemini-powered natural-language reasoning.

It allows a store manager to ask questions in plain language and receive answers grounded in the application's own retail data.

The system identifies:

- Products likely to run out of stock
- Overstocked products
- Sales spikes
- Sales drops
- Products requiring attention
- Stores requiring attention
- Recommended actions

When the available data cannot answer a question, the system clearly says so instead of guessing.

## Core Features

### Sales Intelligence

- Product sales performance
- Monthly sales comparison
- Sales growth and decline
- Sales spike and drop detection
- Store-level sales analysis
- Historical sales analysis

### Inventory Intelligence

- Current stock monitoring
- Low-stock detection
- Stock-out risk detection
- Overstock detection
- Inventory coverage calculation
- Reorder recommendations

### Attention Center

The system identifies the issues that require management attention and prioritizes them based on available sales and inventory signals.

### Natural-Language Copilot

Managers can ask questions such as:

- What products are likely to run out?
- Which products are overstocked?
- How did this product perform this month?
- Which store needs attention?
- Why did sales drop?
- What should I prioritize today?

### Evidence-Based Answers

Every important business claim is supported by actual application data.

Example:

Product: Wireless Mouse  
Current Stock: 18 units  
Average Daily Sales: 7.2 units  
Inventory Coverage: 2.5 days  
Reorder Level: 30 units  
Status: High Stock-Out Risk

The recommendation is generated from these verified values rather than invented figures.

### Uncertainty Handling

If the available data cannot answer a question, the system does not fabricate an answer.

Example:

User: How are our Europe stores performing?

Response: The available dataset does not contain Europe store data, so the question cannot be answered from the available information.

## Architecture

                         USER
                           |
                           v
                      FRONTEND
                           |
                           v
                        FASTAPI
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
          SQLITE       ANALYTICS     RETRIEVAL
             |           ENGINE            |
             |              |              |
             +--------------+--------------+
                            |
                            v
                          GEMINI
                            |
                            v
                   GROUNDED RESPONSE
                            |
                 +----------+----------+
                 |          |          |
                 v          v          v
               ANSWER    EVIDENCE   RECOMMENDATION

## Deterministic Logic

Python handles business facts and calculations:

- Total sales
- Revenue calculations
- Sales growth and decline
- Average daily sales
- Inventory coverage
- Reorder-level comparison
- Stock-out detection
- Overstock detection
- Sales trend detection
- Priority scoring
- Data validation

## Gemini Responsibilities

Gemini handles:

- Natural-language understanding
- Explanation of analytical findings
- Interpretation of retrieved context
- Recommendation generation
- Natural-language responses

Gemini is not treated as the source of truth for business numbers.

## Grounded Retrieval

Retail Data -> Data Processing -> Gemini Embeddings -> Local Index -> Similarity Search -> Relevant Context -> Gemini -> Grounded Answer

The retrieval pipeline is local and uses the application's own data and generated supporting information.

## Technology Stack

- Python 3.11
- FastAPI
- SQLite
- Pandas
- NumPy
- Gemini API
- gemini-embedding-001
- Local retrieval
- HTML
- CSS
- JavaScript

## Database

SQLite is used as the local database.

Database tables:

- stores
- products
- sales
- inventory

No hosted database service is required.

## Data

No dataset is provided for PS03.

The project therefore uses its own generated retail data.

The dataset contains:

- Multiple stores
- Multiple products
- Daily sales
- Historical sales
- Current inventory
- Reorder levels
- Stock thresholds
- Normal sales behaviour
- Sales spikes
- Sales drops
- Low-stock scenarios
- Overstock scenarios

The dataset is designed to contain both normal and difficult cases.

## Project Structure

retail-intelligence-copilot/
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
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
├── data/
│   ├── retail.db
│   ├── stores.csv
│   ├── products.csv
│   ├── sales.csv
│   └── inventory.csv
├── index/
│   └── embeddings.npy
└── frontend/
    └── dist/

## Environment Configuration

Required environment variable:

GEMINI_API_KEY

Example:

GEMINI_API_KEY=your_gemini_api_key

The actual API key must never be committed to the repository.

The `.env` file must be ignored by Git.

## .env.example

GEMINI_API_KEY=

## .gitignore

.env
.venv/
venv/
__pycache__/
*.pyc

## Installation

Use Python 3.11.

python3.11 -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

## Run

From the repository root:

python app.py

Application:

http://localhost:8000

The complete application starts using `python app.py`.

No second terminal is required.

No separate frontend build command is required during evaluation.

## Evaluation Compatibility

The application is designed for the hackathon evaluation environment.

Python version: 3.11

Installation:

pip install -r requirements.txt

Run:

python app.py

Port:

8000

The application is designed to:

- Start successfully from a clean clone
- Start within the required startup limit
- Respond within the required request limit
- Handle incomplete input
- Handle ambiguous input
- Handle invalid input
- Handle missing data
- Handle unsupported questions
- Handle Gemini failures gracefully
- Use precomputed indexes where required
- Keep generated data inside the repository

## Performance Strategy

To keep startup and request times low:

- Retail data is stored locally
- SQLite is used instead of a hosted database
- Retrieval is local
- Expensive indexing is precomputed where appropriate
- Embeddings are reused instead of unnecessarily regenerated
- Deterministic calculations are lightweight

## Error Handling

The application handles:

- Empty queries
- Invalid input
- Unknown products
- Unknown stores
- Missing data
- Insufficient evidence
- Database failures
- Retrieval failures
- Gemini API failures

The system should fail gracefully instead of crashing.

## External API Policy

Gemini is the only external API used by the application.

The project does not use:

- OpenAI API
- Anthropic API
- Groq API
- Hosted vector databases
- Third-party RAG services
- Third-party memory services
- Other external APIs

Local components such as SQLite, NumPy and local retrieval are used inside the application.

## Security

Never commit:

- API keys
- `.env`
- Secrets
- Virtual environments
- Model weights

Only `.env.example` is committed as the environment template.

## Git Development Strategy

Development will be committed progressively during the 24-hour hackathon so the repository history reflects genuine development.

Recommended progression:

1. Initial project setup
2. Add retail data model
3. Add generated retail dataset
4. Implement sales analytics
5. Implement inventory analytics
6. Implement attention detection
7. Integrate Gemini
8. Implement local retrieval
9. Build AI copilot
10. Add evidence and recommendations
11. Handle difficult cases
12. Improve UI
13. Final testing

Example:

git add .
git commit -m "Implement inventory analytics"

## Test Scenarios

### Normal Case

Question:

What products are likely to run out?

Expected behaviour:

Identify products at stock-out risk, show supporting inventory and sales figures, and provide a recommendation.

### Difficult Case

Question:

What should I prioritize today?

Expected behaviour:

Compare multiple signals such as inventory coverage, sales velocity, sales trends and thresholds, then provide an evidence-backed recommendation.

### No-Data Case

Question:

How are our Europe stores performing?

Expected behaviour:

State that the available data does not contain the required information instead of guessing.

### Sales Trend Case

Question:

Why did sales drop for this product?

Expected behaviour:

Compare historical sales, show the actual values, and explain the detected change.

## Design Principles

### Deterministic First

Business facts and calculations are generated using deterministic Python logic.

### Grounded AI

Gemini responses are based on retrieved information from the application's own data.

### Evidence Over Claims

Important answers expose the actual figures supporting the conclusion.

### Honest Uncertainty

The system explicitly communicates when available data is insufficient.

### Explainable Recommendations

Recommendations show the reasoning, supporting data and assumptions.

### Human Decision Support

The system recommends actions but does not automatically execute business decisions.

## Demo Plan

The final demonstration will show:

1. A normal management query.
2. A difficult prioritization case.
3. Evidence and figures supporting the recommendation.
4. A no-data case where the system refuses to guess.

## Submission

GitHub Repository: TODO

Demo Video: TODO

## Hackathon

NexusTiq24

Track ID: PS03

Problem Statement: Retail - Sales and Inventory Copilot

Backend: Python

Entry Point: app.py

Application Port: 8000
