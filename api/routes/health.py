from fastapi import APIRouter
from api.schemas import HealthResponse
from core.settings_loader import load_settings

router = APIRouter()
settings = load_settings()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Returns service health and configuration info."""
    app_cfg = settings.get("app", {})
    llm_cfg = settings.get("llm", {})
    db_cfg = settings.get("vector_database", {})

    return HealthResponse(
        status="ok",
        app_name=app_cfg.get("name", "chatbot"),
        version=app_cfg.get("version", "unknown"),
        llm_provider=llm_cfg.get("provider", "unknown"),
        llm_model=llm_cfg.get("model_name", "unknown"),
        vector_db=db_cfg.get("type", "unknown"),
        collection=db_cfg.get("collection_name", "unknown"),
    )
