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
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
# If the configured model is not available, try these in order before declaring Gemini unavailable.
GEMINI_FALLBACK_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
]
GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768
HEALTH_CACHE_SECONDS = 60

HOST = "0.0.0.0"
PORT = 8000

# Business clock used by analytics so demos stay reproducible.
BUSINESS_DATE = "2026-09-04"

# Sales velocity window for inventory coverage.
VELOCITY_LOOKBACK_DAYS = 14

# Stock-out coverage thresholds (days of inventory remaining).
# Central rule used by analytics, dashboard, copilot, and policy docs:
#   coverage <= 2              -> critical
#   2 < coverage <= 5          -> high
#   5 < coverage <= 7          -> medium
#   coverage > 7               -> NOT a stock-out risk (below-reorder handled separately)
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
    "store_underperform": 45,
    "replenishment_review": 38,
    "overstock": 30,
}
# Number of ranked priorities returned for "What should I prioritize today?".
PRIORITY_TOP_N = 3
REVENUE_IMPACT_CAP = 25
HIGH_PRIORITY_SCORE = 80
MEDIUM_PRIORITY_SCORE = 50

RETRIEVAL_TOP_K = 4
MAX_QUESTION_LENGTH = 2000
GEMINI_TIMEOUT_SECONDS = 25
GEMINI_MAX_RETRIES = 1
HEALTH_TIMEOUT_SECONDS = 12
