from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import api_router
from app.config import Settings
from app.services.buffer import RollingFlowBuffer
from app.services.worker import BackgroundOrchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings.from_env()
    flow_buffer = RollingFlowBuffer(window_minutes=settings.buffer_window_minutes)
    orchestrator = BackgroundOrchestrator(flow_buffer=flow_buffer, settings=settings)
    app.state.settings = settings
    app.state.flow_buffer = flow_buffer
    app.state.orchestrator = orchestrator
    orchestrator.start()
    try:
        yield
    finally:
        orchestrator.stop()


app = FastAPI(
    title="Continuous Learning IDS",
    description="Base service for rolling traffic collection, anomaly training, and dashboard APIs.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(api_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
