"""Single evaluation entry point for Retail Intelligence Copilot."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.config import BUSINESS_DATE, FRONTEND_DIR, GEMINI_API_KEY, HOST, PORT
from src.database import database_ready, get_product, get_store, list_products, list_stores
from src.llm.gemini import gemini_configured
from src.models.schemas import CopilotRequest
from src.services.copilot import answer_question
from src.services.dashboard import build_dashboard
from src.utils.evidence import get_evidence

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("retail_copilot")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting Retail Intelligence Copilot")
    logger.info("Business date %s", BUSINESS_DATE)
    if not database_ready():
        logger.error("SQLite database is missing or empty at data/retail.db")
        raise RuntimeError("Database is not ready. Commit data/retail.db or run scripts/generate_data.py")
    if not gemini_configured():
        logger.warning("GEMINI_API_KEY is not set; copilot will use deterministic fallbacks")
    else:
        logger.info("Gemini key detected (value not logged)")
    logger.info("Frontend directory: %s", FRONTEND_DIR)
    yield


app = FastAPI(title="Retail Intelligence Copilot", version="1.0.0", lifespan=lifespan)


from src.llm.gemini import gemini_configured, check_health

@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "retail-intelligence-copilot",
        "business_date": BUSINESS_DATE,
        "gemini_configured": check_health(),
        "database_ready": database_ready(),
    }


@app.get("/api/dashboard")
def dashboard() -> dict[str, Any]:
    try:
        return build_dashboard()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Dashboard failure")
        raise HTTPException(status_code=500, detail="Dashboard analytics failed.") from exc


@app.get("/api/attention")
def attention() -> dict[str, Any]:
    data = build_dashboard()
    return {"attention": data["attention"], "assumptions": data["assumptions"]}


@app.get("/api/products")
def products() -> dict[str, Any]:
    return {"products": list_products()}


@app.get("/api/stores")
def stores() -> dict[str, Any]:
    return {"stores": list_stores()}


@app.get("/api/products/{product_id}")
def product_detail(product_id: str) -> dict[str, Any]:
    product = get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in the catalogue.")
    from src.analytics.inventory import inventory_status
    from src.analytics.sales import product_performance

    return {
        "product": product,
        "performance": product_performance(product_id),
        "inventory": inventory_status(product_id),
    }


@app.get("/api/stores/{store_id}")
def store_detail(store_id: str) -> dict[str, Any]:
    store = get_store(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found.")
    from src.analytics.inventory import inventory_status, overstock_items, stockout_risks
    from src.analytics.sales import store_performance

    return {
        "store": store,
        "performance": store_performance(store_id),
        "stockouts": stockout_risks(store_id=store_id)[:10],
        "overstock": overstock_items(store_id=store_id)[:10],
        "inventory_sample": inventory_status(store_id=store_id)[:15],
    }


@app.post("/api/copilot")
def copilot(payload: CopilotRequest) -> dict[str, Any]:
    try:
        return answer_question(payload.question)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Copilot failure")
        return {
            "question": payload.question,
            "answer": "The copilot could not complete this request because of an internal error. No figures were invented.",
            "status": "error",
            "intent": "UNKNOWN",
            "priority": None,
            "findings": [],
            "recommendation": None,
            "assumptions": [],
            "evidence": [],
            "retrieved_policies": [],
            "needs_human_review": True,
            "ai_available": False,
            "clarification": None,
            "missing": str(exc.__class__.__name__),
        }


@app.get("/api/evidence/{evidence_id}")
def evidence_lookup(evidence_id: str) -> dict[str, Any]:
    item = get_evidence(evidence_id)
    if not item:
        raise HTTPException(
            status_code=404,
            detail="Evidence id is not in the current process cache. Open the dashboard or ask the copilot first.",
        )
    return item


if FRONTEND_DIR.exists():
    app.mount("/assets-static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/styles.css")
    def styles() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "styles.css", media_type="text/css")

    @app.get("/app.js")
    def javascript() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "app.js", media_type="application/javascript")


def main() -> None:
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
