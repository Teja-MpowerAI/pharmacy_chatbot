"""
1Health Pharmacy chatbot — FastAPI entrypoint.

    uvicorn main:app --reload --port 8000

Wires together the chat WebSocket, the admin dashboard REST API, and the
Razorpay webhook, with CORS for the website + local dev.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.chat import router as chat_router
from api.dashboard import router as dashboard_router
from api.webhooks.razorpay import router as razorpay_router
from api.webhooks.supabase import router as supabase_router
from services.pubsub import close_bus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger(__name__).info("1Health Pharmacy chatbot starting up")
    yield
    await close_bus()


app = FastAPI(
    title="1Health Pharmacy Chatbot",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(dashboard_router)
app.include_router(razorpay_router)
app.include_router(supabase_router)


@app.get("/")
async def root():
    return {"service": "1Health Pharmacy Chatbot", "status": "ok"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True,
    )
