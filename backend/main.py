from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from .config import get_settings
    from .database import init_db
    from .routers import agents, analytics, chat
    from .services.ai_agent import (
        close_openai_client_pool,
        ensure_openai_client_pool,
    )
    from .services.pocket_rpc import PocketRPCClient
except ImportError:
    from config import get_settings
    from database import init_db
    from routers import agents, analytics, chat
    from services.ai_agent import (
        close_openai_client_pool,
        ensure_openai_client_pool,
    )
    from services.pocket_rpc import PocketRPCClient

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await ensure_openai_client_pool()
    logger.info(PocketRPCClient.startup_note())
    try:
        yield
    finally:
        await close_openai_client_pool()


app = FastAPI(title="PocketAgent API", version="0.1.0", lifespan=lifespan)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(agents.router)
app.include_router(analytics.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "PocketAgent"}
