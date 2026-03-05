# v47 Policy Operations Automation API Contract

## Overview

The Policy Operations Automation API provides endpoints for managing experiment recommendations, including generation, approval, and rejection of promotion/rollback decisions.

**Base URL:** `/api/v2/policy-ops`

**Version:** v47

---

## Modes

The system operates in three modes that control how recommendations are processed:

### AUTO Mode
- **Description:** Recommendations are automatically executed when confidence is high
- **Behavior:**
  - High confidence recommendations (≥95%) are auto-approved
  - Medium/Low confidence recommendations require manual review
  - Rollback recommendations always require manual approval for safety
- **Use case:** Trusted experiments with well-understood metrics

### SUPERVISED Mode
- **Description:** Auto-execution with manual rollback option
- **Behavior:**
  - Promotions can be auto-approved
  - Rollbacks must be manually approved
  - Operators can intervene at any time
- **Use case:** Production experiments where safety is important

### MANUAL Mode
- **Description:** All recommendations require manual approval
- **Behavior:**
  - Every recommendation must be explicitly approved or rejected
  - Audit trail is maintained for all decisions
  - No automatic actions taken
- **Use case:** High-risk experiments or regulatory requirements

---

## Endpoints

### List Recommendations

```
GET /api/v2/policy-ops/recommendations
```

**Query Parameters:**
| Parameter | Type   | Required | Description                                    |
|-----------|--------|----------|------------------------------------------------|
| status    | string | No       | Filter by status (pending, approved, rejected) |
| action    | string | No       | Filter by action (promote, rollback, hold)     |

**Response (200 OK):**
```json
{
  "recommendations": [
    {
      "experiment_id": "exp-001",
      "action": "promote",
      "confidence": "high",
      "status": "pending",
      "variant_score": 0.85,
      "control_score": 0.80,
      "rationale": "PROMOTE recommended: Variant shows 6.2% improvement over control...",
      "created_at": 1709836800.0,
      "resolved_at": null,
      "resolved_by": null,
      "resolution_reason": null,
      "metrics": {
        "sample_size": 1000,
        "confidence_level": 0.97,
        "p_value": 0.02
      }
    }
  ],
  "count": 1,
  "filters": {
    "status": null,
    "action": null
  }
}
```

---

### Get Recommendation Detail

```
GET /api/v2/policy-ops/recommendations/{experiment_id}
```

**Path Parameters:**
| Parameter      | Type   | Required | Description                |
|----------------|--------|----------|----------------------------|
| experiment_id  | string | Yes      | The experiment identifier  |

**Response (200 OK):**
```json
{
  "experiment_id": "exp-001",
  "action": "promote",
  "confidence": "high",
  "status": "pending",
  "variant_score": 0.85,
  "control_score": 0.80,
  "rationale": "PROMOTE recommended: Variant shows 6.2% improvement...",
  "created_at": 1709836800.0,
  "metrics": {
    "sample_size": 1000,
    "confidence_level": 0.97,
    "p_value": 0.02
  }
}
```

**Response (404 Not Found):**
```json
{
  "error": "Not found",
  "message": "No recommendation found for experiment 'exp-001'"
}
```

---

### Approve Recommendation

```
POST /api/v2/policy-ops/recommendations/{experiment_id}/approve
```

**Path Parameters:**
| Parameter      | Type   | Required | Description                |
|----------------|--------|----------|----------------------------|
| experiment_id  | string | Yes      | The experiment identifier  |

**Request Body:**
```json
{
  "operator_id": "user-123",
  "reason": "Approved based on strong metrics and high confidence"
}
```

**Field Requirements:**
| Field       | Type   | Required | Validation              |
|-------------|--------|----------|-------------------------|
| operator_id | string | Yes      | Non-empty string        |
| reason      | string | Yes      | Minimum 10 characters   |

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Recommendation approved for promote",
  "experiment_id": "exp-001",
  "previous_status": "pending",
  "new_status": "approved",
  "action": "promote",
  "approved_by": "user-123",
  "approved_at": 1709836900.0
}
```

**Response (400 Bad Request):**
```json
{
  "error": "Bad request",
  "message": "Cannot approve recommendation with status 'executed'"
}
```

---

### Reject Recommendation

```
POST /api/v2/policy-ops/recommendations/{experiment_id}/reject
```

**Path Parameters:**
| Parameter      | Type   | Required | Description                |
|----------------|--------|----------|----------------------------|
| experiment_id  | string | Yes      | The experiment identifier  |

**Request Body:**
```json
{
  "operator_id": "user-123",
  "reason": "Rejecting due to insufficient sample size concerns"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Recommendation rejected",
  "experiment_id": "exp-001",
  "previous_status": "pending",
  "new_status": "rejected",
  "action": "promote",
  "rejected_by": "user-123",
  "rejected_at": 1709836900.0
}
```

---

### Generate Recommendation

```
POST /api/v2/policy-ops/recommendations/generate
```

**Request Body:**
```json
{
  "experiment_id": "exp-001",
  "variant_score": 0.85,
  "control_score": 0.80,
  "sample_size_variant": 500,
  "sample_size_control": 500,
  "confidence_level": 0.97,
  "p_value": 0.02,
  "conversion_rate": 0.15,
  "error_rate": 0.02,
  "latency_p99": 250
}
```

**Required Fields:**
| Field               | Type   | Description                    |
|---------------------|--------|--------------------------------|
| experiment_id       | string | Experiment identifier          |
| variant_score       | float  | Variant performance score      |
| control_score       | float  | Control performance score      |
| sample_size_variant | int    | Variant sample size            |
| sample_size_control | int    | Control sample size            |
| confidence_level    | float  | Statistical confidence (0-1)   |
| p_value             | float  | Statistical p-value            |

**Optional Fields:**
| Field          | Type   | Description              |
|----------------|--------|--------------------------|
| conversion_rate| float  | Conversion rate          |
| error_rate     | float  | Error rate               |
| latency_p99    | float  | P99 latency in ms        |

**Response (201 Created):**
```json
{
  "success": true,
  "recommendation": {
    "experiment_id": "exp-001",
    "action": "promote",
    "confidence": "high",
    "status": "pending",
    "rationale": "PROMOTE recommended: Variant shows 6.2% improvement..."
  }
}
```

---

### Get Daily Report

```
GET /api/v2/policy-ops/reports/daily
```

**Query Parameters:**
| Parameter | Type   | Required | Default | Description              |
|-----------|--------|----------|---------|--------------------------|
| format    | string | No       | json    | Report format (json/md)  |

**Response JSON format (200 OK):**
```json
{
  "generated_at": 1709836800.0,
  "generated_at_iso": "2024-03-07T16:00:00Z",
  "summary": {
    "total": 10,
    "pending": 3,
    "by_status": {
      "pending": 3,
      "approved": 4,
      "rejected": 2,
      "executed": 1
    }
  },
  "pending_recommendations": [...],
  "all_recommendations": [...]
}
```

**Response Markdown format (200 OK):**
Returns `text/markdown` content with a formatted report.

---

## Data Models

### RecommendationAction (Enum)
- `promote` - Promote variant to control
- `rollback` - Rollback to control
- `hold` - Hold for more data
- `review` - Manual review required

### RecommendationConfidence (Enum)
- `high` - > 95% confidence
- `medium` - 80-95% confidence
- `low` - < 80% confidence

### RecommendationStatus (Enum)
- `pending` - Awaiting decision
- `approved` - Approved for execution
- `rejected` - Rejected
- `executed` - Already executed
- `expired` - Expired without action

### BenchmarkMetrics
```json
{
  "variant_score": 0.85,
  "control_score": 0.80,
  "sample_size_variant": 500,
  "sample_size_control": 500,
  "confidence_level": 0.97,
  "p_value": 0.02,
  "conversion_rate": 0.15,
  "error_rate": 0.02,
  "latency_p99": 250
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "error": "Error type",
  "message": "Human-readable description"
}
```

**HTTP Status Codes:**
| Code | Meaning                                      |
|------|----------------------------------------------|
| 200  | Success                                      |
| 201  | Created successfully                         |
| 400  | Bad request - validation error               |
| 404  | Not found - resource doesn't exist           |
| 500  | Internal server error                        |

---

## Thresholds and Logic

### Rollback Trigger
- Variant score < 90% of control score
- Results in `ROLLBACK` recommendation with `HIGH` confidence
- Rationale includes score comparison

### Promotion Criteria
- Statistically significant (p < 0.05)
- Minimum 5% relative improvement
- Sufficient sample size (≥100)

### Confidence Levels
- **High:** Confidence ≥ 95% AND sample size ≥ 500
- **Medium:** Confidence ≥ 80% AND sample size ≥ 200
- **Low:** All other cases

---

## Python 3.9 Compatibility

This API is designed to be compatible with Python 3.9+. Type hints use `Optional` and `Union` instead of the `|` operator:

```python
# Python 3.10+ syntax (NOT used)
def func(value: str | None) -> dict[str, Any] | None:
    ...

# Python 3.9 compatible syntax (USED)
from typing import Optional, Union, Dict, Any

def func(value: Optional[str]) -> Optional[Dict[str, Any]]:
    ...
```

---

## CLI Usage

### Daily Runner

```bash
# Dry run (no changes)
PYTHONPATH=09-tools python3 scripts/policy_ops_daily.py --dry-run

# Generate reports and process recommendations
PYTHONPATH=09-tools python3 scripts/policy_ops_daily.py

# Send reports (placeholder for future integrations)
PYTHONPATH=09-tools python3 scripts/policy_ops_daily.py --send-report
```

---

## Future Enhancements (v48)

- Slack/Teams webhook integration for notifications
- Email report delivery
- Automatic mode transitions based on experiment maturity
- Machine learning-based recommendation tuning
- Integration with external experiment platforms
