from __future__ import annotations

import argparse
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from onboard_api import build_defaults, run_preview, run_apply
from onboard_report import render_summary

WEB_DIR = Path(__file__).resolve().parent / "web" / "onboard"


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

    @app.post("/api/v1/onboard/apply")
    def apply():
        payload = request.get_json(silent=True) or {}
        decisions = payload.get("decisions")
        if not isinstance(decisions, dict):
            return jsonify({"ok": False, "error": "decisions is required"}), 400

        report = run_apply(
            ides=payload.get("ides", []),
            decisions=decisions,
            shell_file=payload.get("shellFile", ""),
            apply_keys=payload.get("applyKeys", False),
            keys=payload.get("keys", {}),
        )
        return jsonify({"ok": True, "report": report, "summary": render_summary(list(report["ides"].values()))})

    @app.get("/")
    def index():
        return send_from_directory(WEB_DIR, "index.html")

    @app.get("/<path:asset_path>")
    def static_assets(asset_path: str):
        return send_from_directory(WEB_DIR, asset_path)

    return app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("vm-onboard-web")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "serve":
        app = create_app()
        app.run(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
