from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router as api_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine

# Ensure models are registered before create_all.
from app import models  # noqa: F401

settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
STATIC_DIR = WEB_DIR / "static"

app = FastAPI(title=settings.app_name, debug=settings.app_debug)
app.include_router(api_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

HTML_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


def html_page(filename: str) -> FileResponse:
    return FileResponse(WEB_DIR / filename, headers=HTML_HEADERS)


@app.get("/")
def root() -> FileResponse:
    return html_page("index.html")


@app.get("/admin")
def admin_page() -> FileResponse:
    return html_page("admin.html")


@app.get("/my")
def my_page() -> FileResponse:
    return html_page("my.html")


@app.get("/bazi")
def bazi_page() -> FileResponse:
    return html_page("bazi.html")


@app.get("/liuyao")
def liuyao_page() -> FileResponse:
    return html_page("liuyao.html")


@app.get("/dream")
def dream_page() -> FileResponse:
    return html_page("dream.html")


@app.get("/compatibility")
def compatibility_page() -> FileResponse:
    return html_page("compatibility.html")


@app.get("/name-wuge")
def name_wuge_page() -> FileResponse:
    return html_page("name-wuge.html")


@app.get("/tarot")
def tarot_page() -> FileResponse:
    return html_page("tarot.html")


@app.get("/lots")
def lots_page() -> FileResponse:
    return html_page("lots.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.on_event("startup")
def on_startup() -> None:
    if not settings.db_persistence_enabled:
        return

    Base.metadata.create_all(bind=engine)
