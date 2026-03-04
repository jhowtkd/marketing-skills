"""v30 Onboarding API endpoints for first-success-path."""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query, Request

from vm_webapp.db import session_scope
from vm_webapp.models_onboarding import OnboardingEvent, OnboardingFrictionPoint, OnboardingState

# v38: Import prefill functionality
from vm_webapp.onboarding_prefill import (
    UserContext,
    generate_prefill_payload,
    get_prefill_for_user,
    PrefillSource,
)

# v38: Import fast lane functionality
from vm_webapp.onboarding_fast_lane import (
    determine_fast_lane_eligibility,
    get_fast_lane_path,
    get_fast_lane_for_user,
    RiskLevel,
    MINIMUM_CHECKLIST,
)

# v38: Import first run functionality
from vm_webapp.onboarding_first_run import (
    validate_template_selection,
    generate_first_run_plan,
    execute_first_run,
    get_recommended_first_run,
    get_one_click_first_run,
    VALID_TEMPLATES,
)

# v38: Import experiment governance functionality
from vm_webapp.onboarding_ttfv_experiments import (
    assign_user_to_variant,
    evaluate_experiment,
    make_experiment_decision,
    check_guardrails,
    calculate_guardrail_status,
    get_active_experiments,
    Experiment,
    ExperimentStatus,
    ExperimentDecision,
)

router = APIRouter()


# Template definitions (matching frontend templates.ts)
FIRST_SUCCESS_TEMPLATES = [
    {
        "id": "blog-post",
        "name": "Blog Post",
        "description": "Crie conteúdo de blog envolvente e otimizado para SEO",
        "category": "content",
        "icon": "📝",
        "default_prompt": "Escreva um post de blog sobre {tópico} com tom {tom} e aproximadamente {palavras} palavras.",
        "variables": [
            {"name": "tópico", "label": "Tópico", "placeholder": "Ex: Marketing Digital", "required": True},
            {"name": "tom", "label": "Tom de voz", "placeholder": "Ex: Profissional", "required": False},
            {"name": "palavras", "label": "Quantidade de palavras", "placeholder": "Ex: 800", "required": False},
        ],
    },
    {
        "id": "landing-page",
        "name": "Landing Page",
        "description": "Copy de alta conversão para páginas de destino",
        "category": "conversion",
        "icon": "🎯",
        "default_prompt": "Crie copy para landing page de {produto/serviço} focado em {benefício principal}.",
        "variables": [
            {"name": "produto/serviço", "label": "Produto ou Serviço", "placeholder": "Ex: Curso de Marketing", "required": True},
            {"name": "benefício principal", "label": "Benefício Principal", "placeholder": "Ex: Aumentar vendas", "required": True},
        ],
    },
    {
        "id": "social-media",
        "name": "Social Media",
        "description": "Posts engajadores para redes sociais",
        "category": "social",
        "icon": "📱",
        "default_prompt": "Crie {quantidade} posts para {rede social} sobre {tópico} com tom {tom}.",
        "variables": [
            {"name": "quantidade", "label": "Quantidade", "placeholder": "Ex: 3", "required": True},
            {"name": "rede social", "label": "Rede Social", "placeholder": "Ex: Instagram", "required": True},
            {"name": "tópico", "label": "Tópico", "placeholder": "Ex: Lançamento", "required": True},
            {"name": "tom", "label": "Tom", "placeholder": "Ex: Descontraído", "required": False},
        ],
    },
    {
        "id": "email-marketing",
        "name": "Email Marketing",
        "description": "Emails que convertem leads em clientes",
        "category": "email",
        "icon": "✉️",
        "default_prompt": "Escreva um email de {tipo} para {público} sobre {assunto}.",
        "variables": [
            {"name": "tipo", "label": "Tipo de Email", "placeholder": "Ex: Newsletter", "required": True},
            {"name": "público", "label": "Público-alvo", "placeholder": "Ex: Clientes", "required": True},
            {"name": "assunto", "label": "Assunto", "placeholder": "Ex: Nova funcionalidade", "required": True},
        ],
    },
    {
        "id": "google-ads",
        "name": "Google Ads",
        "description": "Anúncios otimizados para Google Ads",
        "category": "ads",
        "icon": "🔍",
        "default_prompt": "Crie {quantidade} variações de anúncio Google Ads para {produto} com foco em {palavra-chave}.",
        "variables": [
            {"name": "quantidade", "label": "Quantidade", "placeholder": "Ex: 3", "required": True},
            {"name": "produto", "label": "Produto", "placeholder": "Ex: Software CRM", "required": True},
            {"name": "palavra-chave", "label": "Palavra-chave Principal", "placeholder": "Ex: CRM gratuito", "required": True},
        ],
    },
    {
        "id": "meta-ads",
        "name": "Meta Ads",
        "description": "Anúncios criativos para Facebook e Instagram",
        "category": "ads",
        "icon": "📢",
        "default_prompt": "Crie copy para anúncio Meta Ads de {produto} destacando {benefício}.",
        "variables": [
            {"name": "produto", "label": "Produto", "placeholder": "Ex: Curso Online", "required": True},
            {"name": "benefício", "label": "Benefício Principal", "placeholder": "Ex: Certificação", "required": True},
        ],
    },
]

RECOMMENDED_TEMPLATE_ID = "blog-post"


# Pydantic models
class OnboardingStateSchema(BaseModel):
    user_id: str
    current_step: Optional[str] = None
    template_id: Optional[str] = None
    has_started: bool = False
    has_completed: bool = False
    duration_ms: Optional[int] = None
    updated_at: Optional[str] = None


class OnboardingEventSchema(BaseModel):
    event: str
    user_id: str
    timestamp: str
    duration_ms: Optional[int] = None
    step: Optional[str] = None
    template_id: Optional[str] = None
    brand_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class OnboardingMetrics(BaseModel):
    total_started: int
    total_completed: int
    completion_rate: float
    average_time_to_first_value_ms: float
    dropoff_by_step: Dict[str, int]


class EventResponse(BaseModel):
    success: bool
    event: str
    user_id: str


class TemplatesResponse(BaseModel):
    templates: List[dict]


# State endpoints
@router.get("/state")
async def get_onboarding_state(user_id: str = Query(...), request: Request = None) -> OnboardingStateSchema:
    """Get onboarding state for a user."""
    engine = request.app.state.engine
    
    with session_scope(engine) as session:
        state = session.get(OnboardingState, user_id)
        if state:
            return OnboardingStateSchema(
                user_id=state.user_id,
                current_step=state.current_step,
                has_started=state.has_started,
                has_completed=state.has_completed,
                duration_ms=state.duration_ms,
                updated_at=state.updated_at.isoformat() if state.updated_at else None,
            )
    
    # Return empty state for new user
    return OnboardingStateSchema(
        user_id=user_id,
        current_step=None,
        has_started=False,
        has_completed=False,
    )


@router.post("/state")
async def update_onboarding_state(state: OnboardingStateSchema, request: Request = None) -> OnboardingStateSchema:
    """Update onboarding state for a user."""
    engine = request.app.state.engine
    
    with session_scope(engine) as session:
        db_state = session.get(OnboardingState, state.user_id)
        if db_state:
            db_state.current_step = state.current_step
            db_state.has_started = state.has_started
            db_state.has_completed = state.has_completed
            db_state.duration_ms = state.duration_ms
            db_state.updated_at = datetime.now(timezone.utc)
            if state.template_id:
                db_state.template_id = state.template_id
        else:
            db_state = OnboardingState(
                user_id=state.user_id,
                current_step=state.current_step,
                has_started=state.has_started,
                has_completed=state.has_completed,
                duration_ms=state.duration_ms,
                template_id=state.template_id,
                updated_at=datetime.now(timezone.utc),
            )
            session.add(db_state)
        
        return OnboardingStateSchema(
            user_id=db_state.user_id,
            current_step=db_state.current_step,
            has_started=db_state.has_started,
            has_completed=db_state.has_completed,
            duration_ms=db_state.duration_ms,
            updated_at=db_state.updated_at.isoformat(),
        )


# Templates endpoints
@router.get("/templates/recommended")
async def get_recommended_template() -> dict:
    """Get the recommended first template."""
    for template in FIRST_SUCCESS_TEMPLATES:
        if template["id"] == RECOMMENDED_TEMPLATE_ID:
            result = template.copy()
            result["is_recommended"] = True
            return result
    
    raise HTTPException(status_code=404, detail="No recommended template found")


@router.get("/templates")
async def get_templates(category: Optional[str] = None) -> TemplatesResponse:
    """Get all first-success templates, optionally filtered by category."""
    templates = FIRST_SUCCESS_TEMPLATES
    
    if category and category != "all":
        templates = [t for t in templates if t["category"] == category]
    
    return TemplatesResponse(templates=templates)


@router.get("/templates/{template_id}")
async def get_template(template_id: str) -> dict:
    """Get a specific template by ID."""
    for template in FIRST_SUCCESS_TEMPLATES:
        if template["id"] == template_id:
            return template
    
    raise HTTPException(status_code=404, detail="Template not found")


# Events endpoints
@router.post("/events")
async def track_event(event: OnboardingEventSchema, request: Request = None) -> EventResponse:
    """Track an onboarding event."""
    engine = request.app.state.engine
    event_id = str(uuid4())
    
    with session_scope(engine) as session:
        db_event = OnboardingEvent(
            event_id=event_id,
            event_type=event.event,
            user_id=event.user_id,
            brand_id=event.brand_id,
            session_id=event.session_id,
            step=event.step,
            template_id=event.template_id,
            duration_ms=event.duration_ms,
            metadata=event.metadata or {},
            created_at=datetime.now(timezone.utc),
        )
        session.add(db_event)
    
    return EventResponse(
        success=True,
        event=event.event,
        user_id=event.user_id,
    )


# Metrics endpoints
@router.get("/metrics")
async def get_metrics(
    brand_id: Optional[str] = Query(None),
    days: int = Query(30),
    request: Request = None
) -> OnboardingMetrics:
    """Get onboarding funnel metrics."""
    engine = request.app.state.engine
    
    with session_scope(engine) as session:
        from datetime import timedelta
        from sqlalchemy import func
        
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Build base query
        query = session.query(OnboardingEvent).filter(OnboardingEvent.created_at >= since)
        if brand_id:
            query = query.filter(OnboardingEvent.brand_id == brand_id)
        
        events = query.all()
        
        # Calculate metrics
        started_events = [e for e in events if e.event_type == "onboarding_started"]
        completed_events = [e for e in events if e.event_type == "onboarding_completed"]
        ttfv_events = [e for e in events if e.event_type == "time_to_first_value"]
        dropoff_events = [e for e in events if e.event_type == "onboarding_dropoff"]
        
        total_started = len(started_events)
        total_completed = len(completed_events)
        completion_rate = total_completed / total_started if total_started > 0 else 0.0
        
        # Calculate average TTFV
        ttfv_durations = [e.duration_ms for e in ttfv_events if e.duration_ms]
        avg_ttfv = sum(ttfv_durations) / len(ttfv_durations) if ttfv_durations else 0.0
        
        # Calculate dropoffs by step
        dropoff_by_step: Dict[str, int] = {}
        for event in dropoff_events:
            step = event.step or "unknown"
            dropoff_by_step[step] = dropoff_by_step.get(step, 0) + 1
    
    return OnboardingMetrics(
        total_started=total_started,
        total_completed=total_completed,
        completion_rate=round(completion_rate, 2),
        average_time_to_first_value_ms=round(avg_ttfv, 2),
        dropoff_by_step=dropoff_by_step,
    )


# Friction metrics endpoint
@router.get("/friction-metrics")
async def get_friction_metrics(
    brand_id: Optional[str] = Query(None),
    request: Request = None
) -> dict:
    """Get friction points with dropoff rates."""
    engine = request.app.state.engine
    
    with session_scope(engine) as session:
        query = session.query(OnboardingFrictionPoint)
        if brand_id:
            query = query.filter(OnboardingFrictionPoint.brand_id == brand_id)
        
        points = query.all()
        
        friction_points = []
        dropoff_rates = {}
        
        for p in points:
            friction_points.append({
                "step_name": p.step_name,
                "dropoff_count": p.dropoff_count,
                "total_count": p.total_count,
            })
            if p.total_count > 0:
                dropoff_rates[p.step_name] = round(p.dropoff_count / p.total_count, 2)
    
    return {
        "friction_points": friction_points,
        "dropoff_rates": dropoff_rates,
    }


# v38: Prefill endpoint schemas
class PrefillRequest(BaseModel):
    user_id: str
    utm_campaign: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    referrer: Optional[str] = None
    email: Optional[str] = None


class PrefillResponse(BaseModel):
    user_id: str
    prefill_source: str
    confidence: str
    fields: Dict[str, str]
    context: Dict[str, bool]


@router.post("/prefill")
async def get_prefill(
    request_data: PrefillRequest,
    request: Request = None
) -> PrefillResponse:
    """Get smart prefill suggestions based on user context.
    
    v38: Friction Killer #1 - reduces onboarding setup time by inferring
    user intent from UTM params, referrer, email domain, or segment.
    """
    # Build user context from request data
    utm_params = {}
    if request_data.utm_campaign:
        utm_params["campaign"] = request_data.utm_campaign
    if request_data.utm_source:
        utm_params["source"] = request_data.utm_source
    if request_data.utm_medium:
        utm_params["medium"] = request_data.utm_medium
    
    context = UserContext(
        user_id=request_data.user_id,
        email=request_data.email,
        utm_params=utm_params,
        referrer=request_data.referrer,
    )
    
    payload = generate_prefill_payload(context)
    
    return PrefillResponse(
        user_id=payload["user_id"],
        prefill_source=payload["prefill_source"],
        confidence=payload["confidence"],
        fields=payload["fields"],
        context=payload["context"],
    )


@router.get("/prefill/{user_id}")
async def get_prefill_for_user_endpoint(
    user_id: str,
    request: Request = None
) -> PrefillResponse:
    """Get prefill for an existing user from database."""
    payload = get_prefill_for_user(user_id)
    
    return PrefillResponse(
        user_id=payload["user_id"],
        prefill_source=payload["prefill_source"],
        confidence=payload["confidence"],
        fields=payload["fields"],
        context=payload["context"],
    )


# v38: Fast Lane endpoint schemas
class FastLaneRequest(BaseModel):
    user_id: str
    email_domain: Optional[str] = None
    signup_source: Optional[str] = None
    has_payment_method: bool = False
    ip_reputation_score: float = 0.5
    segment: Optional[str] = None
    previous_completions: int = 0
    checklist: Dict[str, bool] = {}


class FastLaneResponse(BaseModel):
    user_id: str
    is_fast_lane: bool
    original_steps: List[str]
    remaining_steps: List[str]
    skipped_steps: List[str]
    required_checklist: Dict[str, bool]
    checklist_complete: bool
    estimated_time_saved_minutes: float
    reason: Optional[str] = None
    justification: Optional[str] = None
    risk_level: Optional[str] = None


@router.post("/fast-lane")
async def evaluate_fast_lane(
    request_data: FastLaneRequest,
    request: Request = None
) -> FastLaneResponse:
    """Evaluate and return fast lane path for user.
    
    v38: Friction Killer #2 - eligible users skip non-essential steps
    to reduce TTFV while maintaining required minimum checklist.
    """
    # Build context from request
    context = {
        "email_domain": request_data.email_domain or "",
        "signup_source": request_data.signup_source or "unknown",
        "has_payment_method": request_data.has_payment_method,
        "ip_reputation_score": request_data.ip_reputation_score,
        "segment": request_data.segment,
        "previous_completions": request_data.previous_completions,
    }
    
    # Ensure all required checklist items are present
    checklist = {item: request_data.checklist.get(item, False) for item in MINIMUM_CHECKLIST}
    
    # Determine eligibility and get path
    eligibility = determine_fast_lane_eligibility(
        user_id=request_data.user_id,
        context=context,
        checklist=checklist,
    )
    path = get_fast_lane_path(request_data.user_id, eligibility)
    
    return FastLaneResponse(
        user_id=path["user_id"],
        is_fast_lane=path["is_fast_lane"],
        original_steps=path["original_steps"],
        remaining_steps=path["remaining_steps"],
        skipped_steps=path["skipped_steps"],
        required_checklist=path["required_checklist"],
        checklist_complete=path["checklist_complete"],
        estimated_time_saved_minutes=path["estimated_time_saved_minutes"],
        reason=path.get("reason"),
        justification=path.get("justification"),
        risk_level=path.get("risk_level"),
    )


@router.get("/fast-lane/{user_id}")
async def get_fast_lane_for_user_endpoint(
    user_id: str,
    request: Request = None
) -> FastLaneResponse:
    """Get fast lane configuration for an existing user."""
    path = get_fast_lane_for_user(user_id)
    
    return FastLaneResponse(
        user_id=path["user_id"],
        is_fast_lane=path["is_fast_lane"],
        original_steps=path["original_steps"],
        remaining_steps=path["remaining_steps"],
        skipped_steps=path["skipped_steps"],
        required_checklist=path["required_checklist"],
        checklist_complete=path["checklist_complete"],
        estimated_time_saved_minutes=path["estimated_time_saved_minutes"],
        reason=path.get("reason"),
        justification=path.get("justification"),
        risk_level=path.get("risk_level"),
    )


# v38: One-Click First Run endpoint schemas
class FirstRunValidateRequest(BaseModel):
    template_id: str
    parameters: Dict[str, Any] = {}


class FirstRunValidateResponse(BaseModel):
    valid: bool
    template_id: str
    sanitized_params: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    template_info: Optional[Dict[str, Any]] = None


class FirstRunPlanRequest(BaseModel):
    user_id: str
    template_id: str
    parameters: Dict[str, Any] = {}


class FirstRunPlanResponse(BaseModel):
    user_id: str
    template_id: str
    status: str
    execution_steps: List[str]
    estimated_duration_ms: int
    sanitized_params: Optional[Dict[str, Any]] = None
    fallback_template: Optional[str] = None
    fallback_action: Optional[str] = None
    one_click_ready: bool = False


class FirstRunExecuteRequest(BaseModel):
    user_id: str
    plan: Dict[str, Any]


class FirstRunExecuteResponse(BaseModel):
    success: bool
    user_id: str
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: int = 0
    fallback_options: List[str] = []
    template_used: Optional[str] = None


class FirstRunRecommendRequest(BaseModel):
    user_id: str
    selected_template: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class FirstRunRecommendResponse(BaseModel):
    user_id: str
    recommended_template: str
    one_click_ready: bool
    context_applied: bool = False
    contextualized_params: Dict[str, Any] = {}
    template_info: Optional[Dict[str, Any]] = None
    cta_text: str = "Criar meu primeiro conteúdo"
    fallback_template: Optional[str] = None
    reason: Optional[str] = None


@router.post("/first-run/validate")
async def validate_first_run_template(
    request_data: FirstRunValidateRequest,
    request: Request = None
) -> FirstRunValidateResponse:
    """Validate template selection and sanitize parameters.
    
    v38: Friction Killer #3 - validates one-click first run input.
    """
    result = validate_template_selection(
        template_id=request_data.template_id,
        parameters=request_data.parameters,
    )
    
    return FirstRunValidateResponse(
        valid=result["valid"],
        template_id=result.get("template_id", request_data.template_id),
        sanitized_params=result.get("sanitized_params"),
        error=result.get("error"),
        template_info=result.get("template_info"),
    )


@router.post("/first-run/plan")
async def plan_first_run(
    request_data: FirstRunPlanRequest,
    request: Request = None
) -> FirstRunPlanResponse:
    """Generate a first run execution plan."""
    plan = generate_first_run_plan(
        user_id=request_data.user_id,
        template_id=request_data.template_id,
        parameters=request_data.parameters,
    )
    
    return FirstRunPlanResponse(
        user_id=plan["user_id"],
        template_id=plan["template_id"],
        status=plan["status"],
        execution_steps=plan["execution_steps"],
        estimated_duration_ms=plan["estimated_duration_ms"],
        sanitized_params=plan.get("sanitized_params"),
        fallback_template=plan.get("fallback_template"),
        fallback_action=plan.get("fallback_action"),
        one_click_ready=plan.get("one_click_ready", False),
    )


@router.post("/first-run/execute")
async def execute_first_run_endpoint(
    request_data: FirstRunExecuteRequest,
    request: Request = None
) -> FirstRunExecuteResponse:
    """Execute the first run plan."""
    result = execute_first_run(
        user_id=request_data.user_id,
        plan=request_data.plan,
    )
    
    return FirstRunExecuteResponse(
        success=result["success"],
        user_id=result["user_id"],
        output=result.get("output"),
        error=result.get("error"),
        execution_time_ms=result["execution_time_ms"],
        fallback_options=result.get("fallback_options", []),
        template_used=result.get("template_used"),
    )


@router.post("/first-run/recommend")
async def recommend_first_run(
    request_data: FirstRunRecommendRequest,
    request: Request = None
) -> FirstRunRecommendResponse:
    """Get recommended first run configuration for a user."""
    recommendation = get_recommended_first_run(
        user_id=request_data.user_id,
        selected_template=request_data.selected_template,
        user_context=request_data.context,
    )
    
    return FirstRunRecommendResponse(
        user_id=recommendation["user_id"],
        recommended_template=recommendation["recommended_template"],
        one_click_ready=recommendation["one_click_ready"],
        context_applied=recommendation.get("context_applied", False),
        contextualized_params=recommendation.get("contextualized_params", {}),
        template_info=recommendation.get("template_info"),
        cta_text=recommendation.get("cta_text", "Criar meu primeiro conteúdo"),
        fallback_template=recommendation.get("fallback_template"),
        reason=recommendation.get("reason"),
    )


@router.get("/first-run/templates")
async def get_first_run_templates(
    request: Request = None
) -> Dict[str, Any]:
    """Get available templates for one-click first run."""
    templates = []
    for template_id, template in VALID_TEMPLATES.items():
        if template.is_active:
            templates.append({
                "id": template.template_id,
                "name": template.name,
                "category": template.category,
                "description": template.description,
                "safe_parameters": list(template.safe_parameters.keys()),
            })
    
    return {
        "templates": templates,
        "count": len(templates),
    }


# v38: Experiment Governance endpoint schemas
class ExperimentAssignRequest(BaseModel):
    user_id: str
    experiment_id: str = "v38-onboarding-ttfv-acceleration"


class ExperimentAssignResponse(BaseModel):
    user_id: str
    experiment_id: str
    variant: str
    assigned_at: str


class GuardrailCheckRequest(BaseModel):
    metrics: Dict[str, float]


class GuardrailCheckResponse(BaseModel):
    all_passed: bool
    violations: List[str]
    activation_rate_d1_ok: bool
    onboarding_completion_rate_ok: bool
    incident_rate_ok: bool
    activation_rate_d1_delta_pp: float = 0.0
    onboarding_completion_rate_delta_pp: float = 0.0
    incident_rate_delta: float = 0.0


class GuardrailStatusResponse(BaseModel):
    timestamp: str
    activation_rate_d1: Dict[str, Any]
    onboarding_completion_rate: Dict[str, Any]
    incident_rate: Dict[str, Any]
    overall_status: str


class ExperimentDecisionRequest(BaseModel):
    experiment_id: str
    metrics: Dict[str, float]


class ExperimentDecisionResponse(BaseModel):
    experiment_id: str
    decision: str
    reason: str
    confidence: float
    recommended_action: str


@router.post("/experiments/assign")
async def assign_experiment_variant(
    request_data: ExperimentAssignRequest,
    request: Request = None
) -> ExperimentAssignResponse:
    """Assign user to experiment variant deterministically.
    
    v38: Experiment Governance - deterministic variant assignment.
    """
    assignment = assign_user_to_variant(
        user_id=request_data.user_id,
        experiment_id=request_data.experiment_id,
    )
    
    return ExperimentAssignResponse(
        user_id=assignment.user_id,
        experiment_id=assignment.experiment_id,
        variant=assignment.variant,
        assigned_at=assignment.assigned_at.isoformat(),
    )


@router.post("/experiments/guardrails/check")
async def check_experiment_guardrails(
    request_data: GuardrailCheckRequest,
    request: Request = None
) -> GuardrailCheckResponse:
    """Check experiment metrics against guardrails.
    
    Guardrails:
    - activation_rate_d1 >= -2 p.p.
    - onboarding_completion_rate >= -3 p.p.
    - incident_rate: no increase
    """
    result = check_guardrails(request_data.metrics)
    
    return GuardrailCheckResponse(
        all_passed=result["all_passed"],
        violations=result["violations"],
        activation_rate_d1_ok=result["activation_rate_d1_ok"],
        onboarding_completion_rate_ok=result["onboarding_completion_rate_ok"],
        incident_rate_ok=result["incident_rate_ok"],
        activation_rate_d1_delta_pp=result.get("activation_rate_d1_delta_pp", 0.0),
        onboarding_completion_rate_delta_pp=result.get("onboarding_completion_rate_delta_pp", 0.0),
        incident_rate_delta=result.get("incident_rate_delta", 0.0),
    )


@router.get("/experiments/guardrails/status")
async def get_guardrail_status(
    request: Request = None
) -> GuardrailStatusResponse:
    """Get current guardrail status for monitoring."""
    status = calculate_guardrail_status()
    
    return GuardrailStatusResponse(
        timestamp=status["timestamp"],
        activation_rate_d1=status["activation_rate_d1"],
        onboarding_completion_rate=status["onboarding_completion_rate"],
        incident_rate=status["incident_rate"],
        overall_status=status["overall_status"],
    )


@router.post("/experiments/decision")
async def make_experiment_decision_endpoint(
    request_data: ExperimentDecisionRequest,
    request: Request = None
) -> ExperimentDecisionResponse:
    """Make experiment decision based on metrics and guardrails.
    
    Decisions: promote, hold, rollback
    """
    experiment = Experiment(
        experiment_id=request_data.experiment_id,
        name=request_data.experiment_id,
        status=ExperimentStatus.RUNNING,
    )
    
    decision = make_experiment_decision(experiment, request_data.metrics)
    
    return ExperimentDecisionResponse(
        experiment_id=decision.experiment_id,
        decision=decision.decision.value,
        reason=decision.reason,
        confidence=decision.confidence,
        recommended_action=decision.recommended_action,
    )


@router.get("/experiments/active")
async def get_active_experiments_endpoint(
    request: Request = None
) -> Dict[str, Any]:
    """Get list of active experiments."""
    experiments = get_active_experiments()
    
    return {
        "experiments": [
            {
                "experiment_id": e.experiment_id,
                "name": e.name,
                "status": e.status.value,
                "start_date": e.start_date.isoformat() if e.start_date else None,
                "variants": e.variants,
                "description": e.description,
                "owner": e.owner,
            }
            for e in experiments
        ],
        "count": len(experiments),
    }
