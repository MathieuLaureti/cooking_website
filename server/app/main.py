from fastapi import FastAPI
from app.router import match_checker, recipes

app = FastAPI(root_path="/api")

app.include_router(match_checker.router)
app.include_router(recipes.router)

@app.get("/")
def read_root():
    return {"Message": "Hello World"}
