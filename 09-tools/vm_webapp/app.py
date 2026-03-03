from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from vm_webapp.api import router as api_router
from vm_webapp.api_agent_dag import router as dag_api_router
from vm_webapp.api_approval_optimizer import router as optimizer_api_router
from vm_webapp.api_quality_optimizer import router as quality_optimizer_api_router
from vm_webapp.db import build_engine, init_db
from vm_webapp.event_worker import InProcessEventWorker
from vm_webapp.llm import KimiClient
from vm_webapp.logging_config import configure_structured_logging, request_id_middleware
from vm_webapp.middleware_metrics import PrometheusMetricsMiddleware
from vm_webapp.memory import MemoryIndex
from vm_webapp.orchestrator_v2 import configure_workflow_executor
from vm_webapp.run_engine import RunEngine
from vm_webapp.settings import Settings
from vm_webapp.startup_checks import validate_startup_contract
from vm_webapp.workflow_runtime_v2 import WorkflowRuntimeV2
from vm_webapp.workspace import Workspace
from vm_webapp.api_onboarding_experiments import router as onboarding_experiments_router
from vm_webapp.api_onboarding_personalization import router as onboarding_personalization_router
from vm_webapp.api_onboarding_recovery import router as onboarding_recovery_router
from vm_webapp.api_onboarding_activation import router as onboarding_activation_router
from vm_webapp.api_onboarding_continuity import router as onboarding_continuity_router
from vm_webapp.api_onboarding import router as onboarding_base_router
from vm_webapp.api_predictive_resilience import router as predictive_resilience_router
from vm_webapp.api_outcome_roi import router as outcome_roi_router
from vm_webapp.api_copilot import router as copilot_router
from vm_webapp.api_safety_tuning import router as safety_tuning_router
from vm_webapp.api_adaptive_escalation import router as adaptive_escalation_router
from vm_webapp.api_control_loop import router as control_loop_router
from vm_webapp.api_recovery import router as recovery_router
from vm_webapp.api_approval_learning import router as approval_learning_router
from vm_webapp.api.v2 import v2_router


async def value_error_to_http(_request: Request, exc: ValueError) -> JSONResponse:
    message = str(exc)
    if "stream version conflict" in message:
        return JSONResponse(status_code=409, content={"detail": message})
    return JSONResponse(status_code=400, content={"detail": message})


def create_app(
    settings: Settings | None = None,
    *,
    memory: Any | None = None,
    llm: Any | None = None,
    enable_in_process_worker: bool = True,
) -> FastAPI:
    settings = settings or Settings()
    validate_startup_contract(settings)

    app = FastAPI(title="VM Web App")
    configure_structured_logging(level=str(getattr(settings, "log_level", "INFO")))
    app.middleware("http")(request_id_middleware)
    app.add_middleware(PrometheusMetricsMiddleware)
    app.add_exception_handler(ValueError, value_error_to_http)

    workspace = Workspace(root=settings.vm_workspace_root)
    engine = build_engine(settings.vm_db_path, db_url=settings.vm_db_url)
    init_db(engine)
    memory = memory or MemoryIndex(root=workspace.root / "zvec")
    if llm is None and settings.kimi_api_key:
        llm = KimiClient(base_url=settings.kimi_base_url, api_key=settings.kimi_api_key)
    run_engine = RunEngine(engine=engine, workspace=workspace, memory=memory, llm=llm)
    workflow_runtime = WorkflowRuntimeV2(
        engine=engine,
        workspace=workspace,
        memory=memory,
        llm=llm,
        profiles_path=settings.vm_workflow_profiles_path,
        force_foundation_fallback=settings.vm_workflow_force_foundation_fallback,
        foundation_mode=settings.vm_workflow_foundation_mode,
        llm_model=settings.kimi_model,
    )
    event_worker = InProcessEventWorker(engine=engine) if enable_in_process_worker else None
    configure_workflow_executor(workflow_runtime.process_event)

    app.state.settings = settings
    app.state.workspace = workspace
    app.state.engine = engine
    app.state.memory = memory
    app.state.llm = llm
    app.state.run_engine = run_engine
    app.state.workflow_runtime = workflow_runtime
    app.state.event_worker = event_worker
    app.state.worker_mode = "in_process" if event_worker is not None else "external"

    # ============================================================================
    # V2 Onboarding Telemetry Endpoints (included via api.py)
    # ============================================================================

    # Routers faltantes - Phase 0 Hotfix
    # Note: These routers already include /api/v2/ prefix in their routes
    app.include_router(onboarding_experiments_router)
    app.include_router(onboarding_personalization_router)
    app.include_router(onboarding_recovery_router)
    app.include_router(onboarding_activation_router)
    app.include_router(onboarding_continuity_router)
    # Note: onboarding_base_router is included in api.py
    app.include_router(predictive_resilience_router)
    app.include_router(outcome_roi_router)
    app.include_router(copilot_router)
    app.include_router(safety_tuning_router)
    app.include_router(adaptive_escalation_router)
    app.include_router(control_loop_router)
    app.include_router(recovery_router)
    app.include_router(approval_learning_router)

    # New v2 API structure (Phase 2)
    app.include_router(v2_router)

    app.include_router(api_router, prefix="/api/v1")
    app.include_router(api_router)  # Routes include /api/v2/ prefix directly
    app.include_router(dag_api_router)
    app.include_router(optimizer_api_router)
    app.include_router(quality_optimizer_api_router)

    studio_static_dir = Path(__file__).resolve().parents[1] / "web" / "vm-studio" / "dist"
    if studio_static_dir.exists():
        app.mount("/studio", StaticFiles(directory=studio_static_dir, html=True), name="vm-studio")

    static_dir = Path(__file__).resolve().parents[1] / "web" / "vm-ui" / "dist"
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="vm-ui")
    return app
