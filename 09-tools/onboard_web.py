from __future__ import annotations

from flask import Flask, jsonify

from onboard_api import build_defaults


def create_app() -> Flask:
    app = Flask(__name__, static_folder="web/onboard", static_url_path="/")

    @app.get("/api/v1/health")
    def health():
        return jsonify({"ok": True})

    @app.get("/api/v1/defaults")
    def defaults():
        return jsonify({"ok": True, "defaults": build_defaults(shell_file="")})

    return app
