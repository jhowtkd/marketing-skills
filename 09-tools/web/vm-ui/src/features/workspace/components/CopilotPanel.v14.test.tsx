import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { CopilotPanel } from "./CopilotPanel";

describe("CopilotPanel v14 Segmented Personalization", () => {
  const defaultProps = {
    suggestions: [],
    phase: "initial" as const,
    guardrailApplied: false,
    loading: false,
    onRefresh: vi.fn(),
    onFeedback: vi.fn(),
  };

  it("shows personalized badge when segment is eligible", () => {
    render(
      <CopilotPanel
        {...defaultProps}
        segmentStatus={{
          segment_key: "b1:awareness",
          segment_status: "eligible",
          is_eligible: true,
          segment_runs_total: 50,
          adjustment_factor: 0.08,
        }}
      />
    );

    expect(screen.getByText("Personalização ativa")).toBeInTheDocument();
    expect(screen.getByText("50 runs")).toBeInTheDocument();
  });

  it("shows fallback badge when segment is insufficient volume", () => {
    render(
      <CopilotPanel
        {...defaultProps}
        segmentStatus={{
          segment_key: "b1:awareness",
          segment_status: "insufficient_volume",
          is_eligible: false,
          segment_runs_total: 5,
          adjustment_factor: 0,
        }}
      />
    );

    expect(screen.getByText("Fallback global")).toBeInTheDocument();
    expect(screen.getByText("5/20 runs")).toBeInTheDocument();
  });

  it("shows fallback badge when segment is frozen", () => {
    render(
      <CopilotPanel
        {...defaultProps}
        segmentStatus={{
          segment_key: "b1:awareness",
          segment_status: "frozen",
          is_eligible: false,
          segment_runs_total: 30,
          adjustment_factor: 0,
        }}
      />
    );

    expect(screen.getByText("Fallback global")).toBeInTheDocument();
  });

  it("shows dev info when segment status is provided", () => {
    render(
      <CopilotPanel
        {...defaultProps}
        segmentStatus={{
          segment_key: "b1:awareness",
          segment_status: "eligible",
          is_eligible: true,
          segment_runs_total: 50,
          adjustment_factor: 0.08,
        }}
      />
    );

    // Dev info should be visible
    expect(screen.getByText(/b1:awareness/)).toBeInTheDocument();
    expect(screen.getByText(/eligible/)).toBeInTheDocument();
    expect(screen.getByText(/\+8%/)).toBeInTheDocument();
  });

  it("does not show segment badge when segment status is null", () => {
    render(<CopilotPanel {...defaultProps} segmentStatus={null} />);

    expect(screen.queryByText("Personalização ativa")).not.toBeInTheDocument();
    expect(screen.queryByText("Fallback global")).not.toBeInTheDocument();
  });

});
