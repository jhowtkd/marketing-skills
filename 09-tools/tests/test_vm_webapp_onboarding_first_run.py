"""Tests for v38 onboarding one-click first run functionality."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from vm_webapp.onboarding_first_run import (
    FirstRunTemplate,
    FirstRunPlan,
    FirstRunResult,
    validate_template_selection,
    generate_first_run_plan,
    execute_first_run,
    get_recommended_first_run,
    FALLBACK_TEMPLATES,
)


class TestFirstRunTemplate:
    """Test first run template dataclass."""

    def test_template_creation(self):
        template = FirstRunTemplate(
            template_id="blog-post",
            name="Blog Post",
            category="content",
            safe_parameters={"topic": "string", "tone": "string"},
        )
        assert template.template_id == "blog-post"
        assert template.name == "Blog Post"
        assert "topic" in template.safe_parameters

    def test_template_default_values(self):
        template = FirstRunTemplate(
            template_id="test",
            name="Test",
        )
        assert template.category == "general"
        assert template.safe_parameters == {}
        assert template.is_active is True


class TestValidateTemplateSelection:
    """Test template selection validation."""

    def test_valid_template_selection(self):
        template_id = "blog-post"
        parameters = {"topic": "Marketing Digital", "tone": "Profissional"}
        
        result = validate_template_selection(template_id, parameters)
        
        assert result["valid"] is True
        assert result["template_id"] == template_id
        assert "sanitized_params" in result

    def test_invalid_template_id(self):
        template_id = "invalid-template-123"
        parameters = {"topic": "Test"}
        
        result = validate_template_selection(template_id, parameters)
        
        assert result["valid"] is False
        assert "error" in result
        assert "template" in result["error"].lower()

    def test_parameters_sanitization(self):
        template_id = "blog-post"
        parameters = {
            "topic": "Marketing <script>alert('xss')</script>",
            "tone": "Profissional",
        }
        
        result = validate_template_selection(template_id, parameters)
        
        assert result["valid"] is True
        assert "<script>" not in result["sanitized_params"]["topic"]

    def test_dangerous_parameters_rejected(self):
        template_id = "blog-post"
        parameters = {
            "topic": "Test",
            "__proto__": "pollution",  # Prototype pollution attempt
        }
        
        result = validate_template_selection(template_id, parameters)
        
        assert result["valid"] is True
        assert "__proto__" not in result["sanitized_params"]

    def test_sql_injection_attempt_blocked(self):
        template_id = "blog-post"
        parameters = {
            "topic": "Test'; DROP TABLE users; --",
        }
        
        result = validate_template_selection(template_id, parameters)
        
        assert result["valid"] is True
        # Should sanitize but not reject
        assert "DROP TABLE" not in result["sanitized_params"]["topic"]


class TestGenerateFirstRunPlan:
    """Test first run plan generation."""

    def test_plan_generation_for_valid_template(self):
        user_id = "user-123"
        template_id = "landing-page"
        parameters = {"product": "Curso Online", "benefit": "Certificação"}
        
        plan = generate_first_run_plan(user_id, template_id, parameters)
        
        assert plan["user_id"] == user_id
        assert plan["template_id"] == template_id
        assert plan["status"] == "ready"
        assert "execution_steps" in plan
        assert len(plan["execution_steps"]) > 0
        assert "estimated_duration_ms" in plan

    def test_plan_includes_fallback_for_invalid_template(self):
        user_id = "user-123"
        template_id = "nonexistent"
        parameters = {}
        
        plan = generate_first_run_plan(user_id, template_id, parameters)
        
        assert plan["status"] == "fallback"
        assert plan["fallback_template"] in FALLBACK_TEMPLATES

    def test_plan_includes_error_handling(self):
        user_id = "user-123"
        template_id = "social-media"
        parameters = {}  # Missing required parameters
        
        plan = generate_first_run_plan(user_id, template_id, parameters)
        
        assert "fallback_action" in plan
        assert plan["fallback_action"] == "prompt_for_input"

    def test_plan_estimated_duration(self):
        user_id = "user-123"
        template_id = "blog-post"
        parameters = {"topic": "Test"}
        
        plan = generate_first_run_plan(user_id, template_id, parameters)
        
        assert plan["estimated_duration_ms"] > 0
        assert plan["estimated_duration_ms"] < 30000  # Less than 30 seconds


class TestExecuteFirstRun:
    """Test first run execution."""

    def test_successful_execution(self):
        user_id = "user-123"
        plan = {
            "template_id": "blog-post",
            "parameters": {"topic": "Marketing", "tone": "Professional"},
        }
        
        result = execute_first_run(user_id, plan)
        
        assert result["success"] is True
        assert result["user_id"] == user_id
        assert "output" in result
        assert "execution_time_ms" in result

    def test_execution_with_error_fallback(self):
        user_id = "user-123"
        plan = {
            "template_id": "invalid",
            "parameters": {},
        }
        
        result = execute_first_run(user_id, plan)
        
        assert result["success"] is False
        assert "error" in result
        assert "fallback_options" in result
        assert len(result["fallback_options"]) > 0

    def test_execution_includes_output(self):
        user_id = "user-123"
        plan = {
            "template_id": "blog-post",
            "parameters": {"topic": "SEO", "tone": "Informative"},
        }
        
        result = execute_first_run(user_id, plan)
        
        assert "output" in result
        assert isinstance(result["output"], dict)

    def test_execution_time_tracking(self):
        user_id = "user-123"
        plan = {
            "template_id": "email-marketing",
            "parameters": {"type": "Newsletter"},
        }
        
        result = execute_first_run(user_id, plan)
        
        assert "execution_time_ms" in result
        assert result["execution_time_ms"] >= 0


class TestGetRecommendedFirstRun:
    """Test getting recommended first run for user."""

    def test_recommendation_based_on_template(self):
        user_id = "user-123"
        selected_template = "landing-page"
        
        recommendation = get_recommended_first_run(user_id, selected_template)
        
        assert recommendation["user_id"] == user_id
        assert recommendation["recommended_template"] == selected_template
        assert "one_click_ready" in recommendation

    def test_recommendation_with_context(self):
        user_id = "user-123"
        selected_template = "social-media"
        user_context = {
            "industry": "fashion",
            "audience": "young adults",
        }
        
        recommendation = get_recommended_first_run(
            user_id, selected_template, user_context
        )
        
        assert "contextualized_params" in recommendation
        assert recommendation["context_applied"] is True

    def test_fallback_recommendation(self):
        user_id = "user-123"
        selected_template = "unknown"
        
        recommendation = get_recommended_first_run(user_id, selected_template)
        
        assert recommendation["one_click_ready"] is False
        assert recommendation["fallback_template"] in FALLBACK_TEMPLATES


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_user_id_handled(self):
        user_id = ""
        template_id = "blog-post"
        
        result = validate_template_selection(template_id, {})
        # Should not crash, but may not be valid
        assert isinstance(result, dict)

    def test_very_long_parameters_truncated(self):
        template_id = "blog-post"
        parameters = {
            "topic": "A" * 10000,  # Very long string
        }
        
        result = validate_template_selection(template_id, parameters)
        
        assert result["valid"] is True
        assert len(result["sanitized_params"]["topic"]) < 10000

    def test_unicode_parameters_handled(self):
        template_id = "blog-post"
        parameters = {
            "topic": "Marketing Digital 🚀",
            "tone": "Profissional",
        }
        
        result = validate_template_selection(template_id, parameters)
        
        assert result["valid"] is True
        assert "🚀" in result["sanitized_params"]["topic"]

    def test_nested_parameters_flattened(self):
        template_id = "blog-post"
        parameters = {
            "topic": "Test",
            "nested": {"key": "value"},  # Should be flattened or rejected
        }
        
        result = validate_template_selection(template_id, parameters)
        
        # Either flatten or remove nested structures
        assert result["valid"] is True
        assert "nested" not in result["sanitized_params"] or \
               isinstance(result["sanitized_params"]["nested"], str)
