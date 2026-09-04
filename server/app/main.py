from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.router import auth, match_checker, recipes
from app.seed_admin import seed_admin_if_needed


@asynccontextmanager
async def lifespan(app: FastAPI):
    await seed_admin_if_needed()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(auth.router)
app.include_router(match_checker.router)
app.include_router(recipes.router)


@app.get("/health")
async def read_root():
    return "Hello World"
