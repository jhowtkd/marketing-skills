from __future__ import annotations

from fastapi import FastAPI

from vm_webapp.api import router as api_router
from vm_webapp.db import build_engine, init_db
from vm_webapp.llm import KimiClient
from vm_webapp.memory import MemoryIndex
from vm_webapp.settings import Settings
from vm_webapp.workspace import Workspace


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    app = FastAPI(title="VM Web App")

    workspace = Workspace(root=settings.vm_workspace_root)
    engine = build_engine(settings.vm_db_path)
    init_db(engine)
    memory = MemoryIndex(root=workspace.root / "zvec")

    llm = None
    if settings.kimi_api_key:
        llm = KimiClient(base_url=settings.kimi_base_url, api_key=settings.kimi_api_key)

    app.state.settings = settings
    app.state.workspace = workspace
    app.state.engine = engine
    app.state.memory = memory
    app.state.llm = llm

    app.include_router(api_router, prefix="/api/v1")
    return app
