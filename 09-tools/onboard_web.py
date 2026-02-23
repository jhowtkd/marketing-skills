from __future__ import annotations

from flask import Flask, jsonify


def create_app() -> Flask:
    app = Flask(__name__, static_folder="web/onboard", static_url_path="/")

    @app.get("/api/v1/health")
    def health():
        return jsonify({"ok": True})

    return app
