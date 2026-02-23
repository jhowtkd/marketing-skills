from __future__ import annotations

from flask import Flask, jsonify, request

from onboard_api import build_defaults, run_preview
from onboard_report import render_summary


def create_app() -> Flask:
    app = Flask(__name__, static_folder="web/onboard", static_url_path="/")

    @app.get("/api/v1/health")
    def health():
        return jsonify({"ok": True})

    @app.get("/api/v1/defaults")
    def defaults():
        return jsonify({"ok": True, "defaults": build_defaults(shell_file="")})

    @app.post("/api/v1/onboard/preview")
    def preview():
        payload = request.get_json(silent=True) or {}
        report = run_preview(
            ides=payload.get("ides", []),
            shell_file=payload.get("shellFile", ""),
            apply_keys=payload.get("applyKeys", False),
            keys=payload.get("keys", {}),
        )
        return jsonify({"ok": True, "report": report, "summary": render_summary(list(report["ides"].values()))})

    return app
