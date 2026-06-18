from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from .database import init_db
    from .routers import agents, analytics, chains, chat, wallet
    from .services.pocket_rpc import PocketRPCClient
except ImportError:
    from database import init_db
    from routers import agents, analytics, chains, chat, wallet
    from services.pocket_rpc import PocketRPCClient

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info(PocketRPCClient.startup_note())
    yield


app = FastAPI(title="PocketAgent API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(agents.router)
app.include_router(chains.router)
app.include_router(wallet.router)
app.include_router(analytics.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "PocketAgent"}
