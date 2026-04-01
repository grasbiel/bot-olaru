from fastapi import FastAPI
from src.routes.webhook import router as webhook_router
from src.config import logger

app = FastAPI(
    title="Olaru Bot Middleware",
    description="Interface de comunicação entre Evolution API / Chatwoot e Agno AI Agent.",
    version="2.0.0"
)

@app.on_event("startup")
async def startup_event():
    logger.info("bot_middleware_started", status="online")

@app.get("/")
async def root():
    return {
        "status": "online", 
        "service": "Olaru Bot Middleware",
        "version": "2.0.0"
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(webhook_router, prefix="/api/v1")
