from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.phases.phase1.core.config import settings
from backend.phases.phase1.core.errors import ErrorResponse
from backend.phases.phase1.core.logging import configure_logging, get_logger
from backend.phases.phase3.router import router as phase3_router


configure_logging(settings.app_env)
logger = get_logger(__name__)

app = FastAPI(
    title="Restaurant Recommendation API",
    version="0.1.0",
    description="Phase 1 foundation service",
)
app.include_router(phase3_router)
FRONTEND_DIR = Path(__file__).resolve().parents[4] / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on path=%s", request.url.path)
    payload = ErrorResponse(
        code="INTERNAL_SERVER_ERROR",
        message="Something went wrong. Please try again.",
        details=None,
    )
    return JSONResponse(status_code=500, content=payload.model_dump())
