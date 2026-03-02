"""v30 Onboarding API endpoints for first-success-path."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


# In-memory storage (in production, use proper database)
_onboarding_states: Dict[str, dict] = {}
_onboarding_events: List[dict] = []


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
class OnboardingState(BaseModel):
    user_id: str
    current_step: Optional[str] = None
    has_started: bool = False
    has_completed: bool = False
    duration_ms: Optional[int] = None
    updated_at: Optional[str] = None


class OnboardingEvent(BaseModel):
    event: str
    user_id: str
    timestamp: str
    duration_ms: Optional[int] = None
    step: Optional[str] = None
    template_id: Optional[str] = None


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
async def get_onboarding_state(user_id: str = Query(...)) -> OnboardingState:
    """Get onboarding state for a user."""
    if user_id in _onboarding_states:
        state = _onboarding_states[user_id].copy()
        return OnboardingState(**state)
    
    # Return empty state for new user
    return OnboardingState(
        user_id=user_id,
        current_step=None,
        has_started=False,
        has_completed=False,
    )


@router.post("/state")
async def update_onboarding_state(state: OnboardingState) -> OnboardingState:
    """Update onboarding state for a user."""
    state_dict = state.dict()
    state_dict["updated_at"] = datetime.utcnow().isoformat()
    _onboarding_states[state.user_id] = state_dict
    return OnboardingState(**state_dict)


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
async def track_event(event: OnboardingEvent) -> EventResponse:
    """Track an onboarding event."""
    event_dict = event.dict()
    event_dict["received_at"] = datetime.utcnow().isoformat()
    _onboarding_events.append(event_dict)
    
    return EventResponse(
        success=True,
        event=event.event,
        user_id=event.user_id,
    )


# Metrics endpoints
@router.get("/metrics")
async def get_metrics() -> OnboardingMetrics:
    """Get onboarding funnel metrics."""
    # Calculate metrics from events
    started_events = [e for e in _onboarding_events if e["event"] == "onboarding_started"]
    completed_events = [e for e in _onboarding_events if e["event"] == "onboarding_completed"]
    ttfv_events = [e for e in _onboarding_events if e["event"] == "time_to_first_value"]
    dropoff_events = [e for e in _onboarding_events if e["event"] == "onboarding_dropoff"]
    
    total_started = len(started_events)
    total_completed = len(completed_events)
    completion_rate = total_completed / total_started if total_started > 0 else 0.0
    
    # Calculate average TTFV
    ttfv_durations = [e.get("duration_ms", 0) for e in ttfv_events if e.get("duration_ms")]
    avg_ttfv = sum(ttfv_durations) / len(ttfv_durations) if ttfv_durations else 0.0
    
    # Calculate dropoffs by step
    dropoff_by_step: Dict[str, int] = {}
    for event in dropoff_events:
        step = event.get("step", "unknown")
        dropoff_by_step[step] = dropoff_by_step.get(step, 0) + 1
    
    return OnboardingMetrics(
        total_started=total_started,
        total_completed=total_completed,
        completion_rate=round(completion_rate, 2),
        average_time_to_first_value_ms=round(avg_ttfv, 2),
        dropoff_by_step=dropoff_by_step,
    )
