import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

logging.getLogger("app.mcp_server").setLevel(logging.INFO)
logging.getLogger("app.mcp_auth").setLevel(logging.INFO)
from fastmcp.utilities.lifespan import combine_lifespans

from app.mcp_server import build_mcp_asgi_app
from app.gemini_scheduler import gemini_scheduler
from app.catalog_sanity_worker import catalog_sanity_worker
from app.recipe_import_worker import import_worker
from app.router import alias_review, auth, catalog_sanity, match_checker, mcp_oauth, nutrition, recipe_import, recipes

mcp_asgi = build_mcp_asgi_app()


def _import_worker_disabled() -> bool:
    return os.getenv("DISABLE_IMPORT_WORKER", "").lower() in ("1", "true", "yes")


def _catalog_sanity_worker_disabled() -> bool:
    return os.getenv("DISABLE_CATALOG_SANITY_WORKER", "").lower() in ("1", "true", "yes")


@asynccontextmanager
async def lifespan(app: FastAPI):
    gemini_scheduler.start()
    task = None
    sanity_task = None
    if not _import_worker_disabled():
        task = asyncio.create_task(import_worker())
    if not _catalog_sanity_worker_disabled():
        sanity_task = asyncio.create_task(catalog_sanity_worker())
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if sanity_task is not None:
            sanity_task.cancel()
            try:
                await sanity_task
            except asyncio.CancelledError:
                pass
        await gemini_scheduler.stop()


app = FastAPI(lifespan=combine_lifespans(lifespan, mcp_asgi.lifespan))

app.include_router(mcp_oauth.router)
app.include_router(auth.router)
app.include_router(match_checker.router)
app.include_router(nutrition.router)
app.include_router(alias_review.router)
app.include_router(recipes.router)
app.include_router(recipe_import.router)
app.include_router(catalog_sanity.router)
app.mount("/mcp", mcp_asgi)


@app.get("/health")
async def read_root():
    return "Hello World"
