"""
Policy Operations API (v47)

API endpoints for managing recommendations.
"""

import time
from typing import Optional, Dict, Any, List
from flask import Flask, request, jsonify, Blueprint

from vm_webapp.policy_ops_engine import (
    RecommendationStore,
    RecommendationEngine,
    Recommendation,
    RecommendationStatus,
    RecommendationAction,
    BenchmarkMetrics,
    get_recommendation_store,
    get_recommendation_engine
)


# Blueprint for policy ops routes
policy_ops_api = Blueprint("policy_ops_api", __name__)


def emit_telemetry_event(event_name: str, experiment_id: str, 
                         data: Optional[Dict[str, Any]] = None) -> None:
    """Emit a telemetry event."""
    event_data = {
        "event": event_name,
        "experiment_id": experiment_id,
        "timestamp": time.time(),
        "data": data or {}
    }
    print(f"[TELEMETRY] {event_data}")


# =============================================================================
# Recommendation Endpoints
# =============================================================================

@policy_ops_api.route("/api/v2/policy-ops/recommendations", methods=["GET"])
def list_recommendations():
    """
    GET /api/v2/policy-ops/recommendations
    
    List all recommendations. Query params:
    - status: Filter by status (pending, approved, rejected, executed, expired)
    - action: Filter by action (promote, rollback, hold, review)
    """
    try:
        store = get_recommendation_store()
        
        # Get query parameters
        status_filter = request.args.get("status")
        action_filter = request.args.get("action")
        
        # Get all or pending based on filters
        if status_filter == "pending":
            recommendations = store.list_pending()
        else:
            recommendations = store.list_all()
        
        # Apply filters
        if status_filter and status_filter != "pending":
            recommendations = [
                r for r in recommendations 
                if r.status.value == status_filter
            ]
        
        if action_filter:
            recommendations = [
                r for r in recommendations 
                if r.action.value == action_filter
            ]
        
        return jsonify({
            "recommendations": [rec.to_dict() for rec in recommendations],
            "count": len(recommendations),
            "filters": {
                "status": status_filter,
                "action": action_filter
            }
        }), 200
    
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@policy_ops_api.route("/api/v2/policy-ops/recommendations/<experiment_id>", methods=["GET"])
def get_recommendation_detail(experiment_id: str):
    """
    GET /api/v2/policy-ops/recommendations/{experiment_id}
    
    Get detailed recommendation for an experiment.
    """
    try:
        store = get_recommendation_store()
        recommendation = store.load(experiment_id)
        
        if not recommendation:
            return jsonify({
                "error": "Not found",
                "message": f"No recommendation found for experiment '{experiment_id}'"
            }), 404
        
        return jsonify(recommendation.to_dict()), 200
    
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@policy_ops_api.route("/api/v2/policy-ops/recommendations/<experiment_id>/approve", methods=["POST"])
def approve_recommendation(experiment_id: str):
    """
    POST /api/v2/policy-ops/recommendations/{experiment_id}/approve
    
    Approve a recommendation for execution.
    Body: {operator_id, reason}
    """
    try:
        data = request.get_json(silent=True) or {}
        operator_id = data.get("operator_id")
        reason = data.get("reason")
        
        # Validate
        if not operator_id:
            return jsonify({
                "error": "Bad request",
                "message": "operator_id is required"
            }), 400
        
        if not reason:
            return jsonify({
                "error": "Bad request",
                "message": "reason is required"
            }), 400
        
        if len(reason) < 10:
            return jsonify({
                "error": "Bad request",
                "message": "reason must be at least 10 characters"
            }), 400
        
        store = get_recommendation_store()
        recommendation = store.load(experiment_id)
        
        if not recommendation:
            return jsonify({
                "error": "Not found",
                "message": f"Recommendation for experiment '{experiment_id}' not found"
            }), 404
        
        if recommendation.status != RecommendationStatus.PENDING:
            return jsonify({
                "error": "Bad request",
                "message": f"Cannot approve recommendation with status '{recommendation.status.value}'"
            }), 400
        
        emit_telemetry_event("recommendation_approved", experiment_id, {
            "operator_id": operator_id,
            "action": recommendation.action.value
        })
        
        # Update status
        updated = store.update_status(
            experiment_id,
            RecommendationStatus.APPROVED,
            operator_id,
            reason
        )
        
        return jsonify({
            "success": True,
            "message": f"Recommendation approved for {recommendation.action.value}",
            "experiment_id": experiment_id,
            "previous_status": "pending",
            "new_status": "approved",
            "action": recommendation.action.value,
            "approved_by": operator_id,
            "approved_at": updated.resolved_at
        }), 200
    
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@policy_ops_api.route("/api/v2/policy-ops/recommendations/<experiment_id>/reject", methods=["POST"])
def reject_recommendation(experiment_id: str):
    """
    POST /api/v2/policy-ops/recommendations/{experiment_id}/reject
    
    Reject a recommendation.
    Body: {operator_id, reason}
    """
    try:
        data = request.get_json(silent=True) or {}
        operator_id = data.get("operator_id")
        reason = data.get("reason")
        
        # Validate
        if not operator_id:
            return jsonify({
                "error": "Bad request",
                "message": "operator_id is required"
            }), 400
        
        if not reason:
            return jsonify({
                "error": "Bad request",
                "message": "reason is required"
            }), 400
        
        if len(reason) < 10:
            return jsonify({
                "error": "Bad request",
                "message": "reason must be at least 10 characters"
            }), 400
        
        store = get_recommendation_store()
        recommendation = store.load(experiment_id)
        
        if not recommendation:
            return jsonify({
                "error": "Not found",
                "message": f"Recommendation for experiment '{experiment_id}' not found"
            }), 404
        
        if recommendation.status != RecommendationStatus.PENDING:
            return jsonify({
                "error": "Bad request",
                "message": f"Cannot reject recommendation with status '{recommendation.status.value}'"
            }), 400
        
        emit_telemetry_event("recommendation_rejected", experiment_id, {
            "operator_id": operator_id,
            "action": recommendation.action.value
        })
        
        # Update status
        updated = store.update_status(
            experiment_id,
            RecommendationStatus.REJECTED,
            operator_id,
            reason
        )
        
        return jsonify({
            "success": True,
            "message": "Recommendation rejected",
            "experiment_id": experiment_id,
            "previous_status": "pending",
            "new_status": "rejected",
            "action": recommendation.action.value,
            "rejected_by": operator_id,
            "rejected_at": updated.resolved_at
        }), 200
    
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


# =============================================================================
# Generation Endpoint
# =============================================================================

@policy_ops_api.route("/api/v2/policy-ops/recommendations/generate", methods=["POST"])
def generate_recommendation():
    """
    POST /api/v2/policy-ops/recommendations/generate
    
    Generate a new recommendation for an experiment.
    Body: {
        experiment_id,
        variant_score,
        control_score,
        sample_size_variant,
        sample_size_control,
        confidence_level,
        p_value,
        [conversion_rate],
        [error_rate],
        [latency_p99]
    }
    """
    try:
        data = request.get_json(silent=True) or {}
        
        experiment_id = data.get("experiment_id")
        if not experiment_id:
            return jsonify({
                "error": "Bad request",
                "message": "experiment_id is required"
            }), 400
        
        # Required fields
        required = ["variant_score", "control_score", "sample_size_variant", 
                   "sample_size_control", "confidence_level", "p_value"]
        
        for field in required:
            if field not in data:
                return jsonify({
                    "error": "Bad request",
                    "message": f"'{field}' is required"
                }), 400
        
        # Create metrics
        metrics = BenchmarkMetrics(
            variant_score=float(data["variant_score"]),
            control_score=float(data["control_score"]),
            sample_size_variant=int(data["sample_size_variant"]),
            sample_size_control=int(data["sample_size_control"]),
            confidence_level=float(data["confidence_level"]),
            p_value=float(data["p_value"]),
            conversion_rate=data.get("conversion_rate"),
            error_rate=data.get("error_rate"),
            latency_p99=data.get("latency_p99")
        )
        
        emit_telemetry_event("recommendation_generation_requested", experiment_id, {
            "metrics": metrics.to_dict() if hasattr(metrics, 'to_dict') else str(metrics)
        })
        
        # Generate recommendation
        engine = get_recommendation_engine()
        recommendation = engine.generate_recommendation(experiment_id, metrics)
        
        # Store it
        store = get_recommendation_store()
        store.save(recommendation)
        
        return jsonify({
            "success": True,
            "recommendation": recommendation.to_dict()
        }), 201
    
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


# =============================================================================
# Report Endpoint
# =============================================================================

@policy_ops_api.route("/api/v2/policy-ops/reports/daily", methods=["GET"])
def get_daily_report():
    """
    GET /api/v2/policy-ops/reports/daily
    
    Get daily recommendations report.
    Query params:
    - format: 'json' (default) or 'markdown'
    """
    try:
        from vm_webapp.policy_ops_engine import PolicyOpsReporter
        
        format_type = request.args.get("format", "json")
        store = get_recommendation_store()
        reporter = PolicyOpsReporter(store)
        
        if format_type == "markdown":
            report = reporter.generate_markdown_report()
            return report, 200, {"Content-Type": "text/markdown"}
        else:
            report = reporter.generate_json_report()
            return jsonify(report), 200
    
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.register_blueprint(policy_ops_api)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5001)
