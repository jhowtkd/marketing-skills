import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import UnifiedTaskRail from "./UnifiedTaskRail";
import type { StepStatus, QueueItem } from "./UnifiedTaskRail";

describe("UnifiedTaskRail", () => {
  const defaultSteps = [
    { id: "understand", label: "Entender", order: 1 },
    { id: "ideate", label: "Idear", order: 2 },
    { id: "create", label: "Criar", order: 3 },
    { id: "review", label: "Revisar", order: 4 },
  ];

  const defaultQueue: QueueItem[] = [
    {
      id: "queue-1",
      title: "Aprovar campanha Q1",
      priority: "high",
      status: "pending",
      assignee: "user-1",
      createdAt: "2026-03-01T10:00:00Z",
    },
    {
      id: "queue-2",
      title: "Revisar copy",
      priority: "medium",
      status: "in_progress",
      assignee: "user-2",
      createdAt: "2026-03-01T09:00:00Z",
    },
  ];

  const defaultProps = {
    steps: defaultSteps,
    activeStepId: "ideate",
    completedStepIds: ["understand"],
    stepStatuses: {
      understand: "done" as StepStatus,
      ideate: "active" as StepStatus,
      create: "blocked" as StepStatus,
      review: "pending" as StepStatus,
    },
    queue: defaultQueue,
    onStepSelect: vi.fn(),
    onQueueItemSelect: vi.fn(),
    onStepComplete: vi.fn(),
  };

  describe("rendering", () => {
    it("renders the rail container", () => {
      render(<UnifiedTaskRail {...defaultProps} />);
      expect(screen.getByTestId("unified-task-rail")).toBeInTheDocument();
    });

    it("renders section title", () => {
      render(<UnifiedTaskRail {...defaultProps} />);
      expect(screen.getByText("Etapas & Fila")).toBeInTheDocument();
    });

    it("renders all workflow steps", () => {
      render(<UnifiedTaskRail {...defaultProps} />);
      expect(screen.getByText("Entender")).toBeInTheDocument();
      expect(screen.getByText("Idear")).toBeInTheDocument();
      expect(screen.getByText("Criar")).toBeInTheDocument();
      expect(screen.getByText("Revisar")).toBeInTheDocument();
    });

    it("renders queue section title", () => {
      render(<UnifiedTaskRail {...defaultProps} />);
      expect(screen.getByText("Fila Operacional")).toBeInTheDocument();
    });

    it("renders all queue items", () => {
      render(<UnifiedTaskRail {...defaultProps} />);
      expect(screen.getByText("Aprovar campanha Q1")).toBeInTheDocument();
      expect(screen.getByText("Revisar copy")).toBeInTheDocument();
    });

    it("shows queue item count badge", () => {
      render(<UnifiedTaskRail {...defaultProps} />);
      // Find the badge in the queue header
      const queueHeader = screen.getByTestId("queue-header");
      expect(queueHeader.textContent).toContain("2");
    });
  });

  describe("step states", () => {
    it("marks active step correctly", () => {
      render(<UnifiedTaskRail {...defaultProps} />);
      const activeStep = screen.getByTestId("step-ideate");
      expect(activeStep).toHaveAttribute("data-status", "active");
    });

    it("marks completed steps correctly", () => {
      render(<UnifiedTaskRail {...defaultProps} />);
      const completedStep = screen.getByTestId("step-understand");
      expect(completedStep).toHaveAttribute("data-status", "done");
    });

    it("marks blocked steps correctly", () => {
      render(<UnifiedTaskRail {...defaultProps} />);
      const blockedStep = screen.getByTestId("step-create");
      expect(blockedStep).toHaveAttribute("data-status", "blocked");
    });

    it("marks pending steps correctly", () => {
      render(<UnifiedTaskRail {...defaultProps} />);
      const pendingStep = screen.getByTestId("step-review");
      expect(pendingStep).toHaveAttribute("data-status", "pending");
    });
  });

  describe("queue item states", () => {
    it("shows high priority badge", () => {
      render(<UnifiedTaskRail {...defaultProps} />);
      const highPriorityItem = screen.getByTestId("queue-item-queue-1");
      expect(highPriorityItem).toHaveAttribute("data-priority", "high");
    });

    it("shows medium priority badge", () => {
      render(<UnifiedTaskRail {...defaultProps} />);
      const mediumPriorityItem = screen.getByTestId("queue-item-queue-2");
      expect(mediumPriorityItem).toHaveAttribute("data-priority", "medium");
    });

    it("shows pending status", () => {
      render(<UnifiedTaskRail {...defaultProps} />);
      // Check the queue item with pending status
      const queueItem = screen.getByTestId("queue-item-queue-1");
      expect(queueItem.textContent).toContain("Pendente");
    });

    it("shows in_progress status", () => {
      render(<UnifiedTaskRail {...defaultProps} />);
      expect(screen.getByText("Em progresso")).toBeInTheDocument();
    });
  });

  describe("interactions", () => {
    it("calls onStepSelect when step is clicked", () => {
      const onStepSelect = vi.fn();
      render(<UnifiedTaskRail {...defaultProps} onStepSelect={onStepSelect} />);
      
      fireEvent.click(screen.getByText("Criar"));
      expect(onStepSelect).toHaveBeenCalledWith("create");
    });

    it("calls onQueueItemSelect when queue item is clicked", () => {
      const onQueueItemSelect = vi.fn();
      render(<UnifiedTaskRail {...defaultProps} onQueueItemSelect={onQueueItemSelect} />);
      
      fireEvent.click(screen.getByText("Aprovar campanha Q1"));
      expect(onQueueItemSelect).toHaveBeenCalledWith("queue-1");
    });

    it("calls onStepComplete when complete button is clicked", () => {
      const onStepComplete = vi.fn();
      render(<UnifiedTaskRail {...defaultProps} onStepComplete={onStepComplete} />);
      
      const completeButton = screen.getByTestId("complete-step-ideate");
      fireEvent.click(completeButton);
      expect(onStepComplete).toHaveBeenCalledWith("ideate");
    });
  });

  describe("empty states", () => {
    it("shows empty message when no queue items", () => {
      render(<UnifiedTaskRail {...defaultProps} queue={[]} />);
      expect(screen.getByText("Fila vazia")).toBeInTheDocument();
    });

    it("shows empty message when no steps", () => {
      render(<UnifiedTaskRail {...defaultProps} steps={[]} />);
      expect(screen.getByText("Nenhuma etapa definida")).toBeInTheDocument();
    });
  });

  describe("collapsible sections", () => {
    it("toggles steps section when header is clicked", () => {
      render(<UnifiedTaskRail {...defaultProps} />);
      const stepsHeader = screen.getByTestId("steps-header");
      
      fireEvent.click(stepsHeader);
      expect(screen.queryByTestId("steps-list")).not.toBeInTheDocument();
      
      fireEvent.click(stepsHeader);
      expect(screen.getByTestId("steps-list")).toBeInTheDocument();
    });

    it("toggles queue section when header is clicked", () => {
      render(<UnifiedTaskRail {...defaultProps} />);
      const queueHeader = screen.getByTestId("queue-header");
      
      fireEvent.click(queueHeader);
      expect(screen.queryByTestId("queue-list")).not.toBeInTheDocument();
      
      fireEvent.click(queueHeader);
      expect(screen.getByTestId("queue-list")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("has correct aria-label for steps section", () => {
      render(<UnifiedTaskRail {...defaultProps} />);
      // Check the steps header button has the aria-label
      const stepsHeader = screen.getByTestId("steps-header");
      expect(stepsHeader).toHaveAttribute("aria-label", "Etapas do workflow");
    });

    it("has correct aria-label for queue section", () => {
      render(<UnifiedTaskRail {...defaultProps} />);
      expect(screen.getByLabelText("Fila operacional")).toBeInTheDocument();
    });

    it("marks active step with aria-current", () => {
      render(<UnifiedTaskRail {...defaultProps} />);
      const activeStep = screen.getByTestId("step-ideate");
      expect(activeStep).toHaveAttribute("aria-current", "step");
    });
  });
});
