"""Single evaluation entry point for Retail Intelligence Copilot."""

from __future__ import annotations

import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.config import HOST, PORT, ROOT_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("retail_copilot")

app = FastAPI(title="Retail Intelligence Copilot", version="0.1.0")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "retail-intelligence-copilot"}


frontend_dir = ROOT_DIR / "frontend" / "dist"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
else:

    @app.get("/")
    def root() -> JSONResponse:
        return JSONResponse(
            {
                "service": "Retail Intelligence Copilot",
                "health": "/api/health",
                "note": "Frontend is not built yet.",
            }
        )


def main() -> None:
    logger.info("Starting Retail Intelligence Copilot on %s:%s", HOST, PORT)
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
