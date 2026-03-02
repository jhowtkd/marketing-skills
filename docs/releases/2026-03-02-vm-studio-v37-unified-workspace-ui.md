# VM Studio v37 - Unified Workspace UI

**Release Date:** 2026-03-02  
**Branch:** `feature/governance-v37-unified-workspace-ui`  
**Base Commit:** `09b61da7` (v36 Outcome Attribution & Hybrid ROI Loop)

## Summary

Consolidar operação em um Workspace unificado de 3 colunas com foco em execução, menor troca de contexto e maior velocidade de ação.

### Layout Decisions

| Coluna | Conteúdo | Tipo |
|--------|----------|------|
| **Left** (280px) | Etapas + Fila Operacional | Híbrido |
| **Center** (flex) | Editor/Ação + Timeline Resumida | Split |
| **Right** (320px) | Next Best Actions + Insights/Alertas | Híbrido |

## Changes

### New Components

#### 1. Unified Layout State (`layout/unifiedLayout.ts`)
- Centralized state management for 3-column layout
- Column configuration with width, visibility, collapsibility
- Toggle functions for left/right columns
- Responsive breakpoint support (mobile: 768px, tablet: 1024px)
- Grid template calculation for CSS

#### 2. UnifiedTaskRail (`components/UnifiedTaskRail.tsx`)
- Hybrid workflow steps + operational queue in single rail
- Step states: pending, active, done, blocked
- Queue item priorities: low, medium, high, critical
- Collapsible sections for steps and queue
- Complete button with hover reveal for active steps
- Footer stats showing progress

#### 3. ExecutionCenter (`components/ExecutionCenter.tsx`)
- Split layout: Editor (main) + Timeline (compact)
- Execution statuses: pending, running, completed, error, paused
- Timeline events with type variants and actor tracking
- Secondary actions with variant styling
- Loading state with spinner animation
- "View more" truncation for timeline

#### 4. ActionInsightSidebar (`components/ActionInsightSidebar.tsx`)
- Hybrid Next Actions + Insights + Alerts
- Action impact levels with one-click support
- Insight cards: opportunity, risk, info, success with trends
- Alert items with severity and dismiss functionality
- Priority ordering for actions and alerts
- Collapsible sections

#### 5. UX Telemetry Extensions (`features/ux/telemetry.ts`)
- `trackPrimaryAction`: location tracking (rail/center/sidebar)
- `trackContextSwitch`: counter for context switches per session
- `startStepToActionTracking` + `trackStepToActionLatency`: time to first action
- `trackResponsiveLayout`: mobile/tablet/desktop breakpoints
- `trackWorkspaceInteraction`: component-specific events

### Modified Files

#### WorkspacePanel.tsx
- Integrated unified 3-column layout state
- Added left column wrapper (TaskRail)
- Added right column wrapper (Action/Insights)
- Layout toggle controls in sidebar
- Section navigation buttons

## Metrics

### Target Goals (6 weeks)

| Metric | Target | Measurement |
|--------|--------|-------------|
| time_to_first_action | -20% | trackStepToActionLatency |
| action_success_rate | +15% | Primary action completion rate |
| navigation_error_rate | -25% | trackNavigationError |
| context_switches_per_session | -30% | trackContextSwitch |

### Telemetry Events

```typescript
// Primary action tracking
trackPrimaryAction({ action, location: 'rail'|'center'|'sidebar', stepId? })

// Context switch tracking
trackContextSwitch({ from, to, trigger: 'user'|'system' })
getContextSwitchCount() // Returns session counter

// Step to action latency
startStepToActionTracking(stepId)
trackStepToActionLatency({ stepId, action }) // Calculates latencyMs

// Responsive layout
trackResponsiveLayout({ breakpoint, columnsVisible, leftCollapsed, rightCollapsed })

// Component interactions
trackWorkspaceInteraction({ component, action, details? })
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Unified Workspace v37                        │
├─────────────────┬─────────────────────────┬─────────────────────┤
│   LEFT (280px)  │      CENTER (flex)      │    RIGHT (320px)    │
│                 │                         │                     │
│  ┌───────────┐  │   ┌─────────────────┐   │  ┌───────────────┐  │
│  │  Etapas   │  │   │                 │   │  │  Next Best    │  │
│  │  Workflow │  │   │     Editor      │   │  │    Actions    │  │
│  │           │  │   │                 │   │  │               │  │
│  │  ● Done   │  │   │   [Conteúdo]    │   │  │  High Impact  │  │
│  │  ○ Active │  │   │                 │   │  │  1-clique     │  │
│  │  ◌ Blocked│  │   └─────────────────┘   │  └───────────────┘  │
│  └───────────┘  │                         │                     │
│                 │   ┌─────────────────┐   │  ┌───────────────┐  │
│  ┌───────────┐  │   │  Timeline       │   │  │   Insights    │  │
│  │   Fila    │  │   │  (Compact)      │   │  │               │  │
│  │Operacional│  │   │  • Event 1      │   │  │  ↑ Oportunity │  │
│  │           │  │   │  • Event 2      │   │  │  ⚠ Risk       │  │
│  │ 🔴 High   │  │   │  • Event 3      │   │  │  ℹ Info       │  │
│  │ 🟡 Medium │  │   └─────────────────┘   │  └───────────────┘  │
│  └───────────┘  │                         │                     │
│                 │   [Primary Action]      │  ┌───────────────┐  │
│                 │   [Secondary Actions]   │  │    Alerts     │  │
│                 │                         │  │               │  │
│                 │                         │  │  🚨 Critical  │  │
│                 │                         │  │  ⚠️ Warning   │  │
└─────────────────┴─────────────────────────┴─────────────────────┘
```

## Test Coverage

| Component | Tests |
|-----------|-------|
| unifiedLayout.ts | 14 |
| UnifiedTaskRail | 24 |
| ExecutionCenter | 27 |
| ActionInsightSidebar | 36 |
| WorkspaceUnifiedUx | 17 |
| **Total** | **118** |

## Migration Guide

### For Developers

1. **New Layout State**: Use `createUnifiedLayoutState()` for unified workspace
2. **Telemetry**: Import new tracking functions from `features/ux/telemetry`
3. **Components**: New components are drop-in replacements for existing sections

### Breaking Changes

None - all changes are additive and backward compatible.

## Verification

```bash
# Python tests
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_api_v2.py -q
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_metrics_prometheus.py -q

# Frontend tests
cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/

# Build
cd 09-tools/web/vm-ui && npm run build
```

## Related

- v36: Outcome Attribution & Hybrid ROI Loop
- v35: Cross-Session Continuity Autopilot
- v34: Onboarding Recovery & Reactivation Autopilot
- v29: UX Task-First Redesign

## Authors

- VM Studio Team
