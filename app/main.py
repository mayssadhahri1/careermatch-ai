"""Point d'entrée de l'application FastAPI."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import get_settings
from app.db.database import init_db

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Au démarrage : création des tables
    init_db()
    yield


app = FastAPI(
    title=get_settings().app_name,
    version="1.0.0",
    description="Agent IA qui compare un CV à une offre de stage : score, compétences manquantes, "
    "plan de progression et paragraphe de lettre de motivation.",
    lifespan=lifespan,
)

app.include_router(router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Sert l'interface web."""
    return FileResponse(STATIC_DIR / "index.html")
