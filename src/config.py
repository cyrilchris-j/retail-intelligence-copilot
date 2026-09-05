"""Application configuration and documented business-rule constants."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
INDEX_DIR = ROOT_DIR / "index"
FRONTEND_DIR = ROOT_DIR / "frontend" / "dist"
DB_PATH = DATA_DIR / "retail.db"
EMBEDDINGS_PATH = INDEX_DIR / "embeddings.npy"
CHUNKS_PATH = INDEX_DIR / "chunks.json"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()
GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768

HOST = "0.0.0.0"
PORT = 8000

# Business clock used by analytics so demos stay reproducible.
BUSINESS_DATE = "2026-09-04"

# Sales velocity window for inventory coverage.
VELOCITY_LOOKBACK_DAYS = 14

# Stock-out coverage thresholds (days of inventory remaining).
STOCKOUT_CRITICAL_DAYS = 2.0
STOCKOUT_HIGH_DAYS = 5.0
STOCKOUT_MEDIUM_DAYS = 7.0

# Overstock: coverage above this AND stock above target, with slow velocity.
OVERSTOCK_COVERAGE_DAYS = 45.0
OVERSTOCK_MIN_STOCK_VS_TARGET = 1.5
OVERSTOCK_MAX_DAILY_SALES = 1.5

# Spike / drop: recent window vs immediately preceding baseline window.
TREND_WINDOW_DAYS = 14
SPIKE_CHANGE_PCT = 25.0
DROP_CHANGE_PCT = -25.0

# Attention scoring weights. Higher score = more urgent for the manager.
PRIORITY_WEIGHTS = {
    "stockout_critical": 100,
    "stockout_high": 80,
    "stockout_medium": 55,
    "sales_drop": 50,
    "sales_spike": 35,
    "overstock": 30,
    "store_underperform": 45,
}
REVENUE_IMPACT_CAP = 25
HIGH_PRIORITY_SCORE = 80
MEDIUM_PRIORITY_SCORE = 50

RETRIEVAL_TOP_K = 4
MAX_QUESTION_LENGTH = 2000
GEMINI_TIMEOUT_SECONDS = 25
GEMINI_MAX_RETRIES = 1
