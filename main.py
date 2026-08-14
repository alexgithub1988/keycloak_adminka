from fastapi import FastAPI
from app.api.routes import admin_routes

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Приложение запущено"} 