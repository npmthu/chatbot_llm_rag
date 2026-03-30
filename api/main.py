import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routes import chat, health
from core.settings_loader import load_settings
from core.logging_setup import setup_logging

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

setup_logging()
logger = logging.getLogger("api")
settings = load_settings()
app_cfg = settings.get("app", {})


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {app_cfg.get('name', 'chatbot')} v{app_cfg.get('version', '?')}")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=app_cfg.get("name", "NMK Chatbot"),
    version=app_cfg.get("version", "1.0.0"),
    description="RAG-based chatbot API powered by Qdrant + Ollama",
    lifespan=lifespan,
)

# CORS — allow all origins by default; tighten in production via CORS_ORIGINS env var
_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(health.router, prefix="/api")

# Serve frontend — must be mounted AFTER API routes
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
