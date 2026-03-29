from fastapi import FastAPI
from src.routes.webhook import router as webhook_router

app = FastAPI(title="Olaru Bot Middleware")

@app.get("/")
async def root():
    return {"status": "online", "message": "Olaru Bot Middleware is running!"}

app.include_router(webhook_router)
