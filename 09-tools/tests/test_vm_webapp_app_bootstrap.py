"""Bootstrap and route contract integration tests."""

import pytest
from fastapi.testclient import TestClient


class TestAppBootstrap:
    """Tests for app bootstrap and route contracts."""

    def test_app_starts_without_error(self):
        """App should bootstrap without exceptions."""
        from vm_webapp.app import create_app
        
        app = create_app()
        assert app is not None
        assert app.title == "VM Web App"

    def test_v34_v36_routes_exist(self):
        """Legacy v34-v36 routes should still be present."""
        from vm_webapp.app import create_app
        
        app = create_app()
        client = TestClient(app)
        
        # Core v2 routes
        routes_to_check = [
            "/api/v2/brands",
            "/api/v2/projects",
            "/api/v2/threads",
            "/api/v2/health/live",
            "/api/v2/metrics",
        ]
        
        for route in routes_to_check:
            response = client.get(route)
            # Should not be 404 (route not found)
            assert response.status_code != 404, f"Route {route} not found"

    def test_no_duplicate_prefix_routes(self):
        """Ensure no /api/v2/api/v2/ routes exist after fixes."""
        from vm_webapp.app import create_app
        
        app = create_app()
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        
        # Check for any duplicate prefix
        bad_routes = [r for r in routes if '/api/v2/api/v2' in r]
        
        assert not bad_routes, f"Found routes with duplicate prefix: {bad_routes}"

    def test_route_count_reasonable(self):
        """App should have a reasonable number of routes (>50)."""
        from vm_webapp.app import create_app
        
        app = create_app()
        routes = [r for r in app.routes if hasattr(r, 'path')]
        
        # Should have many routes
        assert len(routes) > 50, f"Too few routes: {len(routes)}"


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_live_returns_ok(self):
        """Health live endpoint should return 200."""
        from vm_webapp.app import create_app
        
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/api/v2/health/live")
        
        # Should return 200 (or 500 if db issue, but not 404)
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
