import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CopilotPanel } from "./CopilotPanel";

describe("CopilotPanel", () => {
  const mockSuggestion = {
    suggestion_id: "sugg-123",
    content: "Profile: engagement, Mode: creative",
    confidence: 0.85,
    reason_codes: ["high_success_rate"],
    why: "Based on historical performance",
    expected_impact: { quality_delta: 10, approval_lift: 8 },
    created_at: "2026-02-28T12:00:00Z",
  };

  const defaultProps = {
    suggestions: [mockSuggestion],
    phase: "initial" as const,
    guardrailApplied: false,
    loading: false,
    onRefresh: vi.fn(),
    onFeedback: vi.fn(),
  };

  it("renders phase suggestions with confidence and why", () => {
    render(<CopilotPanel {...defaultProps} />);

    expect(screen.getByText(/Copilot Editorial/i)).toBeInTheDocument();
    expect(screen.getByText(/85%/)).toBeInTheDocument(); // confidence
    expect(screen.getByText(/Based on historical performance/i)).toBeInTheDocument(); // why
    expect(screen.getByText(/Profile: engagement/i)).toBeInTheDocument();
  });

  it("applies suggestion to request/profile/mode", () => {
    render(<CopilotPanel {...defaultProps} />);

    const applyButton = screen.getByRole("button", { name: /Aplicar/i });
    fireEvent.click(applyButton);

    expect(defaultProps.onFeedback).toHaveBeenCalledWith({
      suggestion_id: "sugg-123",
      action: "accepted",
    });
  });

  it("allows edit before apply and tracks ignore", () => {
    render(<CopilotPanel {...defaultProps} />);

    const editButton = screen.getByRole("button", { name: /Editar/i });
    fireEvent.click(editButton);

    // Edit mode should show textarea
    const textarea = screen.getByPlaceholderText(/Edite a sugestão/i);
    expect(textarea).toBeInTheDocument();

    // Type edited content
    fireEvent.change(textarea, { target: { value: "Modified content" } });

    // Apply edited
    const applyEditedButton = screen.getByRole("button", { name: /Aplicar Edição/i });
    fireEvent.click(applyEditedButton);

    expect(defaultProps.onFeedback).toHaveBeenCalledWith({
      suggestion_id: "sugg-123",
      action: "edited",
      edited_content: "Modified content",
    });
  });

  it("tracks ignore action", () => {
    render(<CopilotPanel {...defaultProps} />);

    const ignoreButton = screen.getByRole("button", { name: /Ignorar/i });
    fireEvent.click(ignoreButton);

    expect(defaultProps.onFeedback).toHaveBeenCalledWith({
      suggestion_id: "sugg-123",
      action: "ignored",
    });
  });

  it("switches between phases", () => {
    const onRefresh = vi.fn();
    render(<CopilotPanel {...defaultProps} onRefresh={onRefresh} />);

    const refineTab = screen.getByRole("button", { name: /Refinar/i });
    fireEvent.click(refineTab);

    expect(onRefresh).toHaveBeenCalledWith("refine");
  });

  it("shows guardrail message when confidence is low", () => {
    render(
      <CopilotPanel
        suggestions={[]}
        phase="initial"
        guardrailApplied={true}
        loading={false}
        onRefresh={vi.fn()}
        onFeedback={vi.fn()}
      />
    );

    expect(screen.getByText(/Confiança insuficiente/i)).toBeInTheDocument();
  });

  it("humanizes reason codes", () => {
    const suggestionWithReasons = {
      ...mockSuggestion,
      reason_codes: ["high_success_rate", "quality", "fast"],
    };

    render(
      <CopilotPanel
        suggestions={[suggestionWithReasons]}
        phase="initial"
        guardrailApplied={false}
        loading={false}
        onRefresh={vi.fn()}
        onFeedback={vi.fn()}
      />
    );

    // Reason codes should be humanized
    expect(screen.getByText(/Alta taxa de sucesso/i)).toBeInTheDocument();
  });

  it("shows loading state", () => {
    render(
      <CopilotPanel
        suggestions={[]}
        phase="initial"
        guardrailApplied={false}
        loading={true}
        onRefresh={vi.fn()}
        onFeedback={vi.fn()}
      />
    );

    expect(screen.getByText(/Carregando sugestões/i)).toBeInTheDocument();
  });

  it("cancels edit mode", () => {
    render(<CopilotPanel {...defaultProps} />);

    const editButton = screen.getByRole("button", { name: /Editar/i });
    fireEvent.click(editButton);

    const textarea = screen.getByPlaceholderText(/Edite a sugestão/i);
    expect(textarea).toBeInTheDocument();

    const cancelButton = screen.getByRole("button", { name: /Cancelar/i });
    fireEvent.click(cancelButton);

    expect(textarea).not.toBeInTheDocument();
  });
});
