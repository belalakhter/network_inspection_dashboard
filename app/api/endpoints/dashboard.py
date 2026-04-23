from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from app.schemas import BufferSnapshot, DashboardResponse, TrainingStatus

router = APIRouter()


@router.get("/", include_in_schema=False)
async def dashboard_index() -> FileResponse:
    return FileResponse("app/static/index.html")


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/dashboard", response_model=DashboardResponse)
async def dashboard_data(request: Request) -> DashboardResponse:
    orchestrator = request.app.state.orchestrator
    return orchestrator.dashboard_snapshot()


@router.get("/api/buffer", response_model=BufferSnapshot)
async def buffer_snapshot(request: Request) -> BufferSnapshot:
    return request.app.state.flow_buffer.snapshot()


@router.get("/api/training-status", response_model=TrainingStatus)
async def training_status(request: Request) -> TrainingStatus:
    orchestrator = request.app.state.orchestrator
    return orchestrator.trainer.status(
        buffer_flow_count=len(request.app.state.flow_buffer),
        next_retrain_in_seconds=orchestrator._seconds_until_retrain(),
        collector_mode=orchestrator.collector_mode,
        last_capture_at=orchestrator._last_capture_at,
        last_capture_flow_count=orchestrator._last_capture_flow_count,
    )
