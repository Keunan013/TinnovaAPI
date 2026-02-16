import httpx
import redis.asyncio as redis

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.veiculos import router as veiculos_router
from app.api.error_handler import register_error_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    app.state.redis = redis.from_url(
        settings.redis_url,
        decode_responses=False,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    app.state.http = httpx.AsyncClient(timeout=10.0)

    yield

    # SHUTDOWN
    await app.state.http.aclose()
    await app.state.redis.aclose()

app = FastAPI(
    title="Tinnova API",
    description="API REST para gerenciamento de veículos.",
    version="1.0.0",
    contact={
        "name": "Keunan Passos Carvalho",
        "email": "keunan.carvalho@gmail.com",
    },
    lifespan=lifespan,
)

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

register_error_handlers(app)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(veiculos_router)
