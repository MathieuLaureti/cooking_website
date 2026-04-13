from fastapi import FastAPI
from app.router import match_checker, recipes


app = FastAPI()


app.include_router(match_checker.router)
app.include_router(recipes.router)


@app.get("/health")
async def read_root():
    return "Hello World"
