from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from vm_webapp.api import router as api_router
from vm_webapp.db import build_engine, init_db
from vm_webapp.llm import KimiClient
from vm_webapp.memory import MemoryIndex
from vm_webapp.orchestrator_v2 import configure_workflow_executor
from vm_webapp.run_engine import RunEngine
from vm_webapp.settings import Settings
from vm_webapp.workflow_runtime_v2 import WorkflowRuntimeV2
from vm_webapp.workspace import Workspace


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
) -> FastAPI:
    settings = settings or Settings()

    app = FastAPI(title="VM Web App")
    app.add_exception_handler(ValueError, value_error_to_http)

    workspace = Workspace(root=settings.vm_workspace_root)
    engine = build_engine(settings.vm_db_path)
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
    )
    configure_workflow_executor(workflow_runtime.execute_thread_run)

    app.state.settings = settings
    app.state.workspace = workspace
    app.state.engine = engine
    app.state.memory = memory
    app.state.llm = llm
    app.state.run_engine = run_engine
    app.state.workflow_runtime = workflow_runtime

    app.include_router(api_router, prefix="/api/v1")
    app.include_router(api_router, prefix="/api")

    static_dir = Path(__file__).resolve().parents[1] / "web" / "vm"
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="vm-ui")
    return app
