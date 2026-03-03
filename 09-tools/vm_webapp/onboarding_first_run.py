"""v38 Onboarding One-Click First Run - accelerates time-to-first-value."""

import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime


@dataclass
class FirstRunTemplate:
    """Template configuration for one-click first run."""
    template_id: str
    name: str
    category: str = "general"
    safe_parameters: Dict[str, str] = field(default_factory=dict)
    is_active: bool = True
    description: str = ""


@dataclass
class FirstRunPlan:
    """Plan for executing first run."""
    user_id: str
    template_id: str
    parameters: Dict[str, Any]
    execution_steps: List[str]
    estimated_duration_ms: int
    status: str = "ready"  # ready, fallback, error
    fallback_template: Optional[str] = None
    fallback_action: Optional[str] = None


@dataclass
class FirstRunResult:
    """Result of first run execution."""
    success: bool
    user_id: str
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: int = 0
    fallback_options: List[str] = field(default_factory=list)


# Valid templates for one-click first run
VALID_TEMPLATES = {
    "blog-post": FirstRunTemplate(
        template_id="blog-post",
        name="Blog Post",
        category="content",
        safe_parameters={"topic": "string", "tone": "string", "words": "number"},
        description="Create an engaging blog post",
    ),
    "landing-page": FirstRunTemplate(
        template_id="landing-page",
        name="Landing Page",
        category="conversion",
        safe_parameters={"product": "string", "benefit": "string"},
        description="High-conversion landing page copy",
    ),
    "social-media": FirstRunTemplate(
        template_id="social-media",
        name="Social Media",
        category="social",
        safe_parameters={"quantity": "number", "network": "string", "topic": "string", "tone": "string"},
        description="Engaging social media posts",
    ),
    "email-marketing": FirstRunTemplate(
        template_id="email-marketing",
        name="Email Marketing",
        category="email",
        safe_parameters={"type": "string", "audience": "string", "subject": "string"},
        description="Emails that convert leads to customers",
    ),
    "google-ads": FirstRunTemplate(
        template_id="google-ads",
        name="Google Ads",
        category="ads",
        safe_parameters={"quantity": "number", "product": "string", "keyword": "string"},
        description="Optimized Google Ads copy",
    ),
    "meta-ads": FirstRunTemplate(
        template_id="meta-ads",
        name="Meta Ads",
        category="ads",
        safe_parameters={"product": "string", "benefit": "string"},
        description="Creative ads for Facebook and Instagram",
    ),
}

# Fallback templates when selection is invalid
FALLBACK_TEMPLATES = ["blog-post", "landing-page", "social-media"]

# Maximum parameter lengths
MAX_PARAM_LENGTH = 500

# Dangerous patterns to sanitize
DANGEROUS_PATTERNS = [
    r'<script[^>]*>.*?</script>',  # Script tags
    r'javascript:',  # JavaScript protocol
    r'on\w+\s*=',  # Event handlers
    r'__proto__',  # Prototype pollution
    r'constructor',  # Constructor access
    r'\{\{[^}]*\}\}',  # Template injection attempts
]

# SQL keywords to sanitize
SQL_KEYWORDS = [
    'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE',
    'EXEC', 'EXECUTE', 'UNION', 'SELECT', 'FROM', 'WHERE',
]


def _sanitize_parameter(value: Any) -> Any:
    """Sanitize a single parameter value."""
    if not isinstance(value, str):
        # Convert non-strings to strings
        return str(value) if value is not None else ""
    
    # Truncate if too long
    if len(value) > MAX_PARAM_LENGTH:
        value = value[:MAX_PARAM_LENGTH] + "..."
    
    # Remove dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        value = re.sub(pattern, '', value, flags=re.IGNORECASE | re.DOTALL)
    
    # Sanitize SQL keywords
    for keyword in SQL_KEYWORDS:
        value = re.sub(r'\b' + keyword + r'\b', '[REMOVED]', value, flags=re.IGNORECASE)
    
    # HTML entity encode remaining HTML-like content
    value = value.replace('<', '&lt;').replace('>', '&gt;')
    
    return value


def _sanitize_parameters(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize all parameters."""
    sanitized = {}
    for key, value in parameters.items():
        # Skip dangerous keys
        if key.startswith('__') or key in ['constructor', 'prototype']:
            continue
        
        # Flatten nested structures
        if isinstance(value, (dict, list)):
            value = str(value)
        
        sanitized[key] = _sanitize_parameter(value)
    
    return sanitized


def validate_template_selection(
    template_id: str,
    parameters: Dict[str, Any],
) -> Dict[str, Any]:
    """Validate template selection and sanitize parameters.
    
    Returns:
        Dict with validation result including sanitized parameters.
    """
    # Check if template exists and is active
    template = VALID_TEMPLATES.get(template_id)
    
    if not template:
        return {
            "valid": False,
            "error": f"Template '{template_id}' not found or inactive",
            "available_templates": list(VALID_TEMPLATES.keys()),
        }
    
    if not template.is_active:
        return {
            "valid": False,
            "error": f"Template '{template_id}' is currently inactive",
        }
    
    # Sanitize parameters
    sanitized_params = _sanitize_parameters(parameters)
    
    # Check for required parameters (optional, can be relaxed for one-click)
    missing_required = []
    for param, param_type in template.safe_parameters.items():
        if param not in sanitized_params or not sanitized_params[param]:
            # For one-click, use defaults instead of failing
            if param_type == "string":
                sanitized_params[param] = "Default"
            elif param_type == "number":
                sanitized_params[param] = "1"
    
    return {
        "valid": True,
        "template_id": template_id,
        "sanitized_params": sanitized_params,
        "template_info": {
            "name": template.name,
            "category": template.category,
            "description": template.description,
        },
    }


def generate_first_run_plan(
    user_id: str,
    template_id: str,
    parameters: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate a first run execution plan.
    
    Creates a plan for one-click first value delivery, with fallback
    handling for invalid templates or parameters.
    """
    # Validate template selection
    validation = validate_template_selection(template_id, parameters)
    
    if not validation["valid"]:
        # Return fallback plan
        fallback = FALLBACK_TEMPLATES[0]
        return {
            "user_id": user_id,
            "template_id": template_id,
            "status": "fallback",
            "fallback_template": fallback,
            "fallback_reason": validation["error"],
            "execution_steps": [
                f"use_fallback_template:{fallback}",
                "apply_default_parameters",
                "generate_content",
                "present_to_user",
            ],
            "estimated_duration_ms": 2000,
            "original_parameters": parameters,
        }
    
    # Check if all required parameters are present (not using defaults)
    template = VALID_TEMPLATES[template_id]
    original_has_all_params = all(
        parameters.get(param) and parameters[param] not in ["Default", "1"]
        for param in template.safe_parameters.keys()
    )
    
    # Check if any defaults were applied
    has_defaults = any(
        validation["sanitized_params"].get(param) in ["Default", "1"]
        for param in template.safe_parameters.keys()
    )
    
    if not original_has_all_params and has_defaults:
        return {
            "user_id": user_id,
            "template_id": template_id,
            "status": "fallback",
            "fallback_action": "prompt_for_input",
            "fallback_reason": "Missing required parameters for one-click execution",
            "execution_steps": [
                "show_parameter_form",
                "collect_missing_inputs",
                "then_execute_first_run",
            ],
            "estimated_duration_ms": 5000,
            "sanitized_params": validation["sanitized_params"],
        }
    
    # Generate full plan
    execution_steps = [
        f"load_template:{template_id}",
        "validate_parameters",
        "prepare_generation_context",
        "generate_content",
        "format_output",
        "save_to_workspace",
        "present_to_user",
    ]
    
    # Estimate duration based on template complexity
    duration_estimates = {
        "blog-post": 3000,
        "landing-page": 2500,
        "social-media": 2000,
        "email-marketing": 2500,
        "google-ads": 2000,
        "meta-ads": 2000,
    }
    
    return {
        "user_id": user_id,
        "template_id": template_id,
        "status": "ready",
        "execution_steps": execution_steps,
        "estimated_duration_ms": duration_estimates.get(template_id, 2500),
        "sanitized_params": validation["sanitized_params"],
        "template_info": validation["template_info"],
        "one_click_ready": True,
    }


def execute_first_run(
    user_id: str,
    plan: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute the first run plan.
    
    Simulates content generation for one-click first value.
    In production, this would integrate with the content generation system.
    """
    start_time = time.time()
    
    template_id = plan.get("template_id", "blog-post")
    status = plan.get("status", "ready")
    
    # Validate template before execution
    if template_id not in VALID_TEMPLATES:
        return {
            "success": False,
            "user_id": user_id,
            "error": f"Invalid template: {template_id}",
            "fallback_options": ["choose_valid_template", "skip_first_run"] + FALLBACK_TEMPLATES[:2],
            "execution_time_ms": 0,
        }
    
    if status == "fallback" and plan.get("fallback_action") == "prompt_for_input":
        return {
            "success": False,
            "user_id": user_id,
            "error": "Additional input required",
            "fallback_options": ["fill_form", "choose_template", "skip_first_run"],
            "execution_time_ms": 0,
        }
    
    # Use fallback template if needed
    if status == "fallback" and plan.get("fallback_template"):
        template_id = plan["fallback_template"]
    
    # Simulate execution time
    estimated_duration = plan.get("estimated_duration_ms", 2500)
    time.sleep(min(estimated_duration / 1000, 0.1))  # Cap at 100ms for tests
    
    execution_time_ms = int((time.time() - start_time) * 1000)
    
    # Generate mock output based on template
    params = plan.get("sanitized_params", {})
    topic = params.get("topic", params.get("product", params.get("type", "Content")))
    
    output = {
        "title": f"Generated {template_id.replace('-', ' ').title()}: {topic}",
        "content_type": template_id,
        "preview": f"This is your first {template_id} about {topic}. Generated in one click!",
        "word_count": 150 if template_id == "blog-post" else 50,
        "saved_to": f"/users/{user_id}/content/first-run",
    }
    
    return {
        "success": True,
        "user_id": user_id,
        "output": output,
        "execution_time_ms": execution_time_ms,
        "template_used": template_id,
    }


def get_recommended_first_run(
    user_id: str,
    selected_template: Optional[str] = None,
    user_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Get recommended first run configuration for a user.
    
    Analyzes user context to recommend the best first run experience.
    """
    context = user_context or {}
    
    # Determine template based on context if not explicitly selected
    template_id = selected_template
    
    if not template_id:
        # Context-based recommendation
        industry = context.get("industry", "").lower()
        
        if industry in ["ecommerce", "retail", "shopify"]:
            template_id = "landing-page"
        elif industry in ["marketing", "agency"]:
            template_id = "blog-post"
        elif industry in ["fashion", "lifestyle", "food"]:
            template_id = "social-media"
        else:
            template_id = FALLBACK_TEMPLATES[0]
    
    # Validate the template
    template = VALID_TEMPLATES.get(template_id)
    
    if not template or not template.is_active:
        return {
            "user_id": user_id,
            "recommended_template": FALLBACK_TEMPLATES[0],
            "one_click_ready": False,
            "fallback_template": FALLBACK_TEMPLATES[0],
            "reason": f"Selected template '{selected_template}' not available",
        }
    
    # Generate contextualized parameters
    contextualized_params = {}
    
    if "industry" in context:
        contextualized_params["topic"] = context["industry"]
    if "audience" in context:
        contextualized_params["tone"] = "Professional"  # Default
    
    return {
        "user_id": user_id,
        "recommended_template": template_id,
        "one_click_ready": True,
        "context_applied": bool(context),
        "contextualized_params": contextualized_params,
        "template_info": {
            "name": template.name,
            "category": template.category,
            "description": template.description,
        },
        "cta_text": "Criar meu primeiro conteúdo",
    }


def get_one_click_first_run(
    user_id: str,
    template_id: str,
    parameters: Dict[str, Any],
) -> Dict[str, Any]:
    """Complete one-click first run flow.
    
    Combines plan generation and execution for a seamless one-click experience.
    """
    # Generate plan
    plan = generate_first_run_plan(user_id, template_id, parameters)
    
    # Execute if ready
    if plan["status"] == "ready":
        result = execute_first_run(user_id, plan)
        return {
            "plan": plan,
            "execution": result,
            "completed": result["success"],
        }
    
    # Return plan for manual execution
    return {
        "plan": plan,
        "execution": None,
        "completed": False,
        "next_action": plan.get("fallback_action", "prompt_for_input"),
    }
