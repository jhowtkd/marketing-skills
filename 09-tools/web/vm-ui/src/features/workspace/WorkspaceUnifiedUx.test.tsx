import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { useEffect, useState } from "react";
import {
  initTelemetry,
  resetTelemetry,
  getTelemetryState,
  trackPrimaryAction,
  trackContextSwitch,
  getContextSwitchCount,
  startStepToActionTracking,
  trackStepToActionLatency,
  trackResponsiveLayout,
  trackWorkspaceInteraction,
} from "../ux/telemetry";
import {
  createUnifiedLayoutState,
  toggleLeftColumn,
  toggleRightColumn,
} from "./layout/unifiedLayout";

describe("Workspace Unified UX Telemetry", () => {
  beforeEach(() => {
    resetTelemetry();
    initTelemetry();
  });

  afterEach(() => {
    resetTelemetry();
  });

  describe("trackPrimaryAction", () => {
    it("tracks primary action from rail location", () => {
      trackPrimaryAction({ action: "start_run", location: "rail", stepId: "create" });
      
      const state = getTelemetryState();
      const actionEvent = state.events.find(e => e.type === "primary_action_clicked");
      
      expect(actionEvent).toBeDefined();
      expect(actionEvent?.action).toBe("start_run");
      expect(actionEvent?.location).toBe("rail");
      expect(actionEvent?.stepId).toBe("create");
    });

    it("tracks primary action from center location", () => {
      trackPrimaryAction({ action: "generate", location: "center" });
      
      const state = getTelemetryState();
      const actionEvent = state.events.find(e => e.type === "primary_action_clicked");
      
      expect(actionEvent?.action).toBe("generate");
      expect(actionEvent?.location).toBe("center");
    });

    it("tracks primary action from sidebar location", () => {
      trackPrimaryAction({ action: "approve", location: "sidebar" });
      
      const state = getTelemetryState();
      const actionEvent = state.events.find(e => e.type === "primary_action_clicked");
      
      expect(actionEvent?.action).toBe("approve");
      expect(actionEvent?.location).toBe("sidebar");
    });
  });

  describe("trackContextSwitch", () => {
    it("tracks context switch by user", () => {
      trackContextSwitch({ from: "execution", to: "queue", trigger: "user" });
      
      const state = getTelemetryState();
      const switchEvent = state.events.find(e => e.type === "context_switch");
      
      expect(switchEvent).toBeDefined();
      expect(switchEvent?.from).toBe("execution");
      expect(switchEvent?.to).toBe("queue");
      expect(switchEvent?.trigger).toBe("user");
    });

    it("tracks context switch by system", () => {
      trackContextSwitch({ from: "queue", to: "insights", trigger: "system" });
      
      const state = getTelemetryState();
      const switchEvent = state.events.find(e => e.type === "context_switch");
      
      expect(switchEvent?.trigger).toBe("system");
    });

    it("increments context switch count", () => {
      trackContextSwitch({ from: "a", to: "b", trigger: "user" });
      trackContextSwitch({ from: "b", to: "c", trigger: "user" });
      trackContextSwitch({ from: "c", to: "d", trigger: "system" });
      
      expect(getContextSwitchCount()).toBe(3);
    });
  });

  describe("trackStepToActionLatency", () => {
    it("tracks latency when action is executed after step", () => {
      // Use fake timers for deterministic latency measurement
      vi.useFakeTimers();
      const T0 = 1000000;
      vi.setSystemTime(T0);
      
      startStepToActionTracking("step-1");
      
      // Simulate 50ms delay using fake time
      vi.setSystemTime(T0 + 50);
      
      trackStepToActionLatency({ stepId: "step-1", action: "generate" });
      
      const state = getTelemetryState();
      const latencyEvent = state.events.find(e => e.type === "step_to_action_latency");
      
      expect(latencyEvent).toBeDefined();
      expect(latencyEvent?.stepId).toBe("step-1");
      expect(latencyEvent?.action).toBe("generate");
      expect(latencyEvent?.latencyMs).toBe(50);
      
      // Cleanup
      vi.useRealTimers();
    });
    
    afterEach(() => {
      // Ensure timers are reset even if test fails
      vi.useRealTimers();
    });

    it("does not track latency if start was not called", () => {
      trackStepToActionLatency({ stepId: "step-2", action: "generate" });
      
      const state = getTelemetryState();
      const latencyEvent = state.events.find(e => e.type === "step_to_action_latency");
      
      expect(latencyEvent).toBeUndefined();
    });
  });

  describe("trackResponsiveLayout", () => {
    it("tracks mobile layout", () => {
      trackResponsiveLayout({
        breakpoint: "mobile",
        columnsVisible: 1,
        leftCollapsed: true,
        rightCollapsed: true,
      });
      
      const state = getTelemetryState();
      const layoutEvent = state.events.find(e => e.type === "responsive_layout_change");
      
      expect(layoutEvent).toBeDefined();
      expect(layoutEvent?.breakpoint).toBe("mobile");
      expect(layoutEvent?.columnsVisible).toBe(1);
    });

    it("tracks desktop layout with all columns visible", () => {
      trackResponsiveLayout({
        breakpoint: "desktop",
        columnsVisible: 3,
        leftCollapsed: false,
        rightCollapsed: false,
      });
      
      const state = getTelemetryState();
      const layoutEvent = state.events.find(e => e.type === "responsive_layout_change");
      
      expect(layoutEvent?.breakpoint).toBe("desktop");
      expect(layoutEvent?.columnsVisible).toBe(3);
    });

    it("tracks layout with collapsed sidebars", () => {
      trackResponsiveLayout({
        breakpoint: "tablet",
        columnsVisible: 2,
        leftCollapsed: false,
        rightCollapsed: true,
      });
      
      const state = getTelemetryState();
      const layoutEvent = state.events.find(e => e.type === "responsive_layout_change");
      
      expect(layoutEvent?.rightCollapsed).toBe(true);
    });
  });

  describe("trackWorkspaceInteraction", () => {
    it("tracks task rail interaction", () => {
      trackWorkspaceInteraction({
        component: "unified_task_rail",
        action: "step_complete",
        details: { stepId: "understand" },
      });
      
      const state = getTelemetryState();
      const interactionEvent = state.events.find(e => e.type === "workspace_interaction");
      
      expect(interactionEvent).toBeDefined();
      expect(interactionEvent?.component).toBe("unified_task_rail");
      expect(interactionEvent?.action).toBe("step_complete");
      expect(interactionEvent?.details).toEqual({ stepId: "understand" });
    });

    it("tracks execution center interaction", () => {
      trackWorkspaceInteraction({
        component: "execution_center",
        action: "primary_action_click",
      });
      
      const state = getTelemetryState();
      const interactionEvent = state.events.find(e => e.type === "workspace_interaction");
      
      expect(interactionEvent?.component).toBe("execution_center");
    });

    it("tracks sidebar interaction", () => {
      trackWorkspaceInteraction({
        component: "action_insight_sidebar",
        action: "insight_click",
        details: { insightId: "insight-1" },
      });
      
      const state = getTelemetryState();
      const interactionEvent = state.events.find(e => e.type === "workspace_interaction");
      
      expect(interactionEvent?.component).toBe("action_insight_sidebar");
    });
  });

  describe("integration with layout state", () => {
    it("tracks layout changes when columns are toggled", () => {
      const layoutState = createUnifiedLayoutState();
      
      // Toggle left column
      const newState = toggleLeftColumn(layoutState);
      trackResponsiveLayout({
        breakpoint: "desktop",
        columnsVisible: newState.columns.filter(c => c.visible).length,
        leftCollapsed: newState.leftCollapsed,
        rightCollapsed: newState.rightCollapsed,
      });
      
      const telemetryState = getTelemetryState();
      const layoutEvent = telemetryState.events.find(e => e.type === "responsive_layout_change");
      
      expect(layoutEvent?.leftCollapsed).toBe(true);
      expect(layoutEvent?.columnsVisible).toBe(2);
    });
  });
});

// Test component that simulates workspace interactions
function TestWorkspaceComponent() {
  const [activeStep, setActiveStep] = useState<string | null>(null);
  const [context, setContext] = useState("execution");

  useEffect(() => {
    initTelemetry();
    return () => resetTelemetry();
  }, []);

  const handleStepSelect = (stepId: string) => {
    startStepToActionTracking(stepId);
    setActiveStep(stepId);
    trackWorkspaceInteraction({
      component: "unified_task_rail",
      action: "step_select",
      details: { stepId },
    });
  };

  const handleContextSwitch = (newContext: string) => {
    trackContextSwitch({
      from: context,
      to: newContext,
      trigger: "user",
    });
    setContext(newContext);
  };

  const handlePrimaryAction = () => {
    if (activeStep) {
      trackStepToActionLatency({
        stepId: activeStep,
        action: "generate",
      });
      trackPrimaryAction({
        action: "generate",
        location: "center",
        stepId: activeStep,
      });
    }
  };

  return (
    <div>
      <button data-testid="step-1" onClick={() => handleStepSelect("step-1")}>
        Step 1
      </button>
      <button data-testid="context-queue" onClick={() => handleContextSwitch("queue")}>
        Switch to Queue
      </button>
      <button data-testid="primary-action" onClick={handlePrimaryAction}>
        Generate
      </button>
    </div>
  );
}

describe("Workspace Component Integration", () => {
  beforeEach(() => {
    resetTelemetry();
  });

  afterEach(() => {
    resetTelemetry();
  });

  it("tracks step selection and subsequent action", async () => {
    render(<TestWorkspaceComponent />);
    
    // Select step
    fireEvent.click(screen.getByTestId("step-1"));
    
    // Wait a bit
    await new Promise(resolve => setTimeout(resolve, 10));
    
    // Execute action
    fireEvent.click(screen.getByTestId("primary-action"));
    
    const state = getTelemetryState();
    
    // Verify step selection was tracked
    const stepInteraction = state.events.find(
      e => e.type === "workspace_interaction" && e.action === "step_select"
    );
    expect(stepInteraction).toBeDefined();
    expect(stepInteraction?.details?.stepId).toBe("step-1");
    
    // Verify latency was tracked
    const latencyEvent = state.events.find(e => e.type === "step_to_action_latency");
    expect(latencyEvent).toBeDefined();
    expect(latencyEvent?.stepId).toBe("step-1");
    
    // Verify primary action was tracked
    const primaryActionEvent = state.events.find(e => e.type === "primary_action_clicked");
    expect(primaryActionEvent).toBeDefined();
    expect(primaryActionEvent?.action).toBe("generate");
  });

  it("tracks context switches", () => {
    render(<TestWorkspaceComponent />);
    
    fireEvent.click(screen.getByTestId("context-queue"));
    
    const state = getTelemetryState();
    const contextSwitchEvent = state.events.find(e => e.type === "context_switch");
    
    expect(contextSwitchEvent).toBeDefined();
    expect(contextSwitchEvent?.from).toBe("execution");
    expect(contextSwitchEvent?.to).toBe("queue");
  });
});
