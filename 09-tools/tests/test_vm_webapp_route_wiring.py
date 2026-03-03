"""Test route wiring to ensure no duplicated /api/v2/api/v2/ prefixes."""

import pytest
from fastapi.testclient import TestClient


class TestRouteWiring:
    """Tests for correct API route wiring without duplicate prefixes."""

    def test_critical_routes_exist_without_duplicate_prefix(self):
        """Verify critical routes exist at /api/v2/* not /api/v2/api/v2/*."""
        from vm_webapp.app import create_app
        
        app = create_app()
        client = TestClient(app)
        
        # Get all routes
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        
        # Critical routes that must exist
        critical_routes = [
            "/api/v2/brands",
            "/api/v2/projects",
            "/api/v2/threads",
        ]
        
        for route in critical_routes:
            # Must exist without duplicate prefix
            matching = [r for r in routes if route in r and "api/v2/api/v2" not in r]
            assert matching, f"Critical route {route} not found or has duplicate prefix"
    
    def test_no_duplicate_api_v2_prefix_in_any_route(self):
        """Ensure no route contains /api/v2/api/v2/ pattern."""
        from vm_webapp.app import create_app
        
        app = create_app()
        
        # Get all route paths
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        
        # Check for duplicate prefix
        duplicate_routes = [r for r in routes if "/api/v2/api/v2" in r]
        
        assert not duplicate_routes, (
            f"Found routes with duplicate /api/v2 prefix: {duplicate_routes}"
        )
    
    def test_brands_endpoint_accessible(self):
        """Test that /api/v2/brands returns 200 (not 404 or 422 from bad wiring)."""
        from vm_webapp.app import create_app
        
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/api/v2/brands")
        # Should be 200 (empty list) or 500 (db issue), NOT 404 (route not found)
        assert response.status_code != 404, "Route /api/v2/brands not found"
        assert response.status_code != 422, "Route has duplicate prefix causing 422"
