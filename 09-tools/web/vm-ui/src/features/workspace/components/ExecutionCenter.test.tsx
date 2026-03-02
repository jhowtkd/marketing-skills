import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ExecutionCenter from "./ExecutionCenter";
import type { TimelineEvent } from "./ExecutionCenter";

describe("ExecutionCenter", () => {
  const defaultTimeline: TimelineEvent[] = [
    {
      id: "evt-1",
      type: "start",
      title: "Run iniciado",
      timestamp: "2026-03-01T10:00:00Z",
      actor: "sistema",
    },
    {
      id: "evt-2",
      type: "stage_complete",
      title: "Stage completado",
      description: "Research finalizado",
      timestamp: "2026-03-01T10:05:00Z",
      actor: "sistema",
    },
    {
      id: "evt-3",
      type: "approval",
      title: "Aprovação humana",
      description: "Aguardando review",
      timestamp: "2026-03-01T10:10:00Z",
      actor: "user-1",
    },
  ];

  const defaultProps = {
    editorContent: "Conteúdo do artefato principal",
    editorTitle: "Versão Ativa",
    status: "running" as const,
    statusLabel: "Em execução",
    primaryActionLabel: "Gerar nova versão",
    primaryActionDisabled: false,
    onPrimaryAction: vi.fn(),
    timeline: defaultTimeline,
    onTimelineEventClick: vi.fn(),
  };

  describe("rendering", () => {
    it("renders the execution center container", () => {
      render(<ExecutionCenter {...defaultProps} />);
      expect(screen.getByTestId("execution-center")).toBeInTheDocument();
    });

    it("renders editor section with title", () => {
      render(<ExecutionCenter {...defaultProps} />);
      expect(screen.getByText("Versão Ativa")).toBeInTheDocument();
    });

    it("renders editor content", () => {
      render(<ExecutionCenter {...defaultProps} />);
      expect(screen.getByText("Conteúdo do artefato principal")).toBeInTheDocument();
    });

    it("renders status badge", () => {
      render(<ExecutionCenter {...defaultProps} />);
      expect(screen.getByText("Em execução")).toBeInTheDocument();
    });

    it("renders primary action button", () => {
      render(<ExecutionCenter {...defaultProps} />);
      expect(screen.getByText("Gerar nova versão")).toBeInTheDocument();
    });

    it("renders timeline section", () => {
      render(<ExecutionCenter {...defaultProps} />);
      expect(screen.getByText("Timeline")).toBeInTheDocument();
    });

    it("renders all timeline events", () => {
      render(<ExecutionCenter {...defaultProps} />);
      expect(screen.getByText("Run iniciado")).toBeInTheDocument();
      expect(screen.getByText("Stage completado")).toBeInTheDocument();
      expect(screen.getByText("Aprovação humana")).toBeInTheDocument();
    });
  });

  describe("status states", () => {
    it("shows running status with correct styling", () => {
      render(<ExecutionCenter {...defaultProps} status="running" />);
      const statusBadge = screen.getByTestId("status-badge");
      expect(statusBadge).toHaveAttribute("data-status", "running");
    });

    it("shows completed status with correct styling", () => {
      render(<ExecutionCenter {...defaultProps} status="completed" statusLabel="Concluído" />);
      const statusBadge = screen.getByTestId("status-badge");
      expect(statusBadge).toHaveAttribute("data-status", "completed");
    });

    it("shows error status with correct styling", () => {
      render(<ExecutionCenter {...defaultProps} status="error" statusLabel="Erro" />);
      const statusBadge = screen.getByTestId("status-badge");
      expect(statusBadge).toHaveAttribute("data-status", "error");
    });

    it("shows pending status with correct styling", () => {
      render(<ExecutionCenter {...defaultProps} status="pending" statusLabel="Pendente" />);
      const statusBadge = screen.getByTestId("status-badge");
      expect(statusBadge).toHaveAttribute("data-status", "pending");
    });
  });

  describe("primary action", () => {
    it("calls onPrimaryAction when button is clicked", () => {
      const onPrimaryAction = vi.fn();
      render(<ExecutionCenter {...defaultProps} onPrimaryAction={onPrimaryAction} />);
      
      fireEvent.click(screen.getByText("Gerar nova versão"));
      expect(onPrimaryAction).toHaveBeenCalledTimes(1);
    });

    it("disables button when primaryActionDisabled is true", () => {
      render(<ExecutionCenter {...defaultProps} primaryActionDisabled={true} />);
      const button = screen.getByText("Gerar nova versão");
      expect(button).toBeDisabled();
    });

    it("shows loading state", () => {
      render(
        <ExecutionCenter
          {...defaultProps}
          isLoading={true}
          loadingMessage="Processando..."
        />
      );
      // Check for loading spinner and message in the editor area
      const editorSection = screen.getByLabelText("Editor de conteúdo");
      expect(editorSection.textContent).toContain("Processando...");
    });
  });

  describe("timeline interactions", () => {
    it("calls onTimelineEventClick when event is clicked", () => {
      const onTimelineEventClick = vi.fn();
      render(
        <ExecutionCenter
          {...defaultProps}
          onTimelineEventClick={onTimelineEventClick}
        />
      );
      
      fireEvent.click(screen.getByText("Run iniciado"));
      expect(onTimelineEventClick).toHaveBeenCalledWith("evt-1");
    });

    it("shows event timestamps", () => {
      render(<ExecutionCenter {...defaultProps} />);
      // Check that timestamps are rendered
      const timestamps = screen.getAllByTestId("timeline-timestamp");
      expect(timestamps.length).toBeGreaterThan(0);
    });

    it("shows event actors", () => {
      render(<ExecutionCenter {...defaultProps} />);
      // Check that actors are shown in the timeline
      const timeline = screen.getByLabelText("Timeline de eventos");
      expect(timeline.textContent).toContain("sistema");
      expect(timeline.textContent).toContain("user-1");
    });
  });

  describe("editor variations", () => {
    it("renders with empty content message", () => {
      render(<ExecutionCenter {...defaultProps} editorContent="" />);
      expect(screen.getByText("Nenhum conteúdo disponível")).toBeInTheDocument();
    });

    it("renders custom editor title", () => {
      render(<ExecutionCenter {...defaultProps} editorTitle="Preview do Email" />);
      expect(screen.getByText("Preview do Email")).toBeInTheDocument();
    });
  });

  describe("secondary actions", () => {
    it("renders secondary actions when provided", () => {
      const secondaryActions = [
        { label: "Salvar rascunho", onClick: vi.fn(), disabled: false },
        { label: "Cancelar", onClick: vi.fn(), disabled: true },
      ];
      render(
        <ExecutionCenter {...defaultProps} secondaryActions={secondaryActions} />
      );
      expect(screen.getByText("Salvar rascunho")).toBeInTheDocument();
      expect(screen.getByText("Cancelar")).toBeInTheDocument();
    });

    it("calls secondary action onClick when clicked", () => {
      const saveDraft = vi.fn();
      const secondaryActions = [
        { label: "Salvar rascunho", onClick: saveDraft, disabled: false },
      ];
      render(
        <ExecutionCenter {...defaultProps} secondaryActions={secondaryActions} />
      );
      
      fireEvent.click(screen.getByText("Salvar rascunho"));
      expect(saveDraft).toHaveBeenCalledTimes(1);
    });
  });

  describe("compact timeline", () => {
    it("renders timeline in compact mode by default", () => {
      render(<ExecutionCenter {...defaultProps} />);
      const timeline = screen.getByTestId("compact-timeline");
      expect(timeline).toBeInTheDocument();
    });

    it("limits timeline events when maxEvents is set", () => {
      render(<ExecutionCenter {...defaultProps} maxTimelineEvents={2} />);
      const events = screen.getAllByTestId("timeline-event");
      expect(events.length).toBe(2);
    });

    it("shows 'view more' link when timeline is truncated", () => {
      render(<ExecutionCenter {...defaultProps} maxTimelineEvents={2} />);
      expect(screen.getByText(/ver mais/i)).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("has correct aria-label for editor section", () => {
      render(<ExecutionCenter {...defaultProps} />);
      expect(screen.getByLabelText("Editor de conteúdo")).toBeInTheDocument();
    });

    it("has correct aria-label for timeline section", () => {
      render(<ExecutionCenter {...defaultProps} />);
      expect(screen.getByLabelText("Timeline de eventos")).toBeInTheDocument();
    });

    it("primary action has aria-busy when loading", () => {
      render(<ExecutionCenter {...defaultProps} isLoading={true} />);
      const button = screen.getByRole("button", { name: /carregando/i });
      expect(button).toHaveAttribute("aria-busy", "true");
    });
  });
});
