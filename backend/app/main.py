from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.router import router as api_router
from app.core.config import get_settings
from app.core.site_gate import request_has_site_gate
from app.db.base import Base
from app.db.session import engine

# Ensure models are registered before create_all.
from app import models  # noqa: F401

settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
STATIC_DIR = WEB_DIR / "static"
ASSET_DIR = BASE_DIR.parent / "static"

app = FastAPI(title=settings.app_name, debug=settings.app_debug)
app.include_router(api_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
if ASSET_DIR.exists():
    app.mount("/assets", StaticFiles(directory=ASSET_DIR), name="assets")

HTML_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}

SITE_GATE_PUBLIC_PREFIXES = (
    "/static/",
    "/assets/",
    "/favicon.ico",
    "/healthz",
    "/api/v1/site-gate/",
)


def _is_site_gate_public(path: str) -> bool:
    if path == "/":
        return True
    return any(path.startswith(prefix) for prefix in SITE_GATE_PUBLIC_PREFIXES)


class SiteGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.site_gate_enabled:
            return await call_next(request)

        path = request.url.path
        if _is_site_gate_public(path):
            return await call_next(request)

        if request_has_site_gate(request):
            return await call_next(request)

        if path.startswith("/api/"):
            return JSONResponse(
                status_code=401,
                content={"detail": "site gate required"},
            )

        return RedirectResponse(url="/", status_code=302)


app.add_middleware(SiteGateMiddleware)


def html_page(filename: str) -> FileResponse:
    return FileResponse(WEB_DIR / filename, headers=HTML_HEADERS)


@app.get("/")
def root(request: Request):
    if settings.site_gate_enabled and request_has_site_gate(request):
        return RedirectResponse(url="/home", status_code=302)
    return html_page("gate.html")


@app.get("/home")
def home_page() -> FileResponse:
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
