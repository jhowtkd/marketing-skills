/**
 * Tests for PolicyDetail component
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PolicyDetail } from "../PolicyDetail";
import type { RolloutPolicy } from "../../../api/rolloutDashboard";

function buildMockPolicy(overrides: Record<string, unknown> = {}): RolloutPolicy {
  return {
    experiment_id: "exp-001",
    active_variant: "variant-A",
    mode: "SUPERVISED",
    status: "pending_review",
    last_evaluation_at: "2026-03-04T10:00:00Z",
    promotion_criteria: {
      min_evaluations: 100,
      min_success_rate: 0.95,
      max_error_rate: 0.01,
    },
    timeline: [
      {
        timestamp: "2026-03-04T10:00:00Z",
        action: "evaluation_completed",
        operator: "system",
        reason: "Met promotion criteria",
      },
      {
        timestamp: "2026-03-04T09:00:00Z",
        action: "evaluation_started",
        operator: "system",
        reason: null,
      },
    ],
    metrics: {
      total_evaluations: 150,
      success_rate: 0.96,
      avg_latency_ms: 45.5,
      error_rate: 0.005,
    },
    can_rollback: false,
    ...overrides,
  };
}

describe("PolicyDetail", () => {
  describe("Rendering", () => {
    it("does not render when isExpanded is false", () => {
      const policy = buildMockPolicy();
      render(<PolicyDetail policy={policy} isExpanded={false} />);

      expect(screen.queryByText("Policy Configuration")).not.toBeInTheDocument();
    });

    it("renders when isExpanded is true", () => {
      const policy = buildMockPolicy();
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText("Policy Configuration")).toBeInTheDocument();
    });
  });

  describe("Policy Configuration Section", () => {
    it("displays experiment ID", () => {
      const policy = buildMockPolicy({ experiment_id: "test-exp-123" });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText("test-exp-123")).toBeInTheDocument();
    });

    it("displays active variant", () => {
      const policy = buildMockPolicy({ active_variant: "variant-B" });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText("variant-B")).toBeInTheDocument();
    });

    it("displays 'None' when active_variant is null", () => {
      const policy = buildMockPolicy({ active_variant: null });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText("None")).toBeInTheDocument();
    });

    it("displays mode", () => {
      const policy = buildMockPolicy({ mode: "AUTOMATIC" });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText("AUTOMATIC")).toBeInTheDocument();
    });

    it("displays status with spaces", () => {
      const policy = buildMockPolicy({ status: "pending_review" });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText("pending review")).toBeInTheDocument();
    });

    it("displays last evaluation timestamp", () => {
      const policy = buildMockPolicy({ last_evaluation_at: "2026-03-04T10:00:00Z" });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      // Date format may vary by locale, but should contain some recognizable part
      expect(screen.getByText(/Mar|2026|10:00/)).toBeInTheDocument();
    });

    it("displays 'Never' when last_evaluation_at is null", () => {
      const policy = buildMockPolicy({ last_evaluation_at: null });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText("Never")).toBeInTheDocument();
    });
  });

  describe("Promotion Criteria Section", () => {
    it("displays min evaluations", () => {
      const policy = buildMockPolicy({
        promotion_criteria: { min_evaluations: 500, min_success_rate: 0.95, max_error_rate: 0.01 },
      });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText("500")).toBeInTheDocument();
    });

    it("displays min success rate as percentage", () => {
      const policy = buildMockPolicy({
        promotion_criteria: { min_evaluations: 100, min_success_rate: 0.95, max_error_rate: 0.01 },
      });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText("95.0%")).toBeInTheDocument();
    });

    it("displays max error rate as percentage", () => {
      const policy = buildMockPolicy({
        promotion_criteria: { min_evaluations: 100, min_success_rate: 0.95, max_error_rate: 0.01 },
      });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText("1.0%")).toBeInTheDocument();
    });
  });

  describe("Timeline Section", () => {
    it("displays timeline events", () => {
      const policy = buildMockPolicy({
        timeline: [
          { timestamp: "2026-03-04T10:00:00Z", action: "test_action", operator: "admin", reason: "Test" },
        ],
      });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText("test_action")).toBeInTheDocument();
    });

    it("displays operator name when available", () => {
      const policy = buildMockPolicy({
        timeline: [
          { timestamp: "2026-03-04T10:00:00Z", action: "test", operator: "admin-user", reason: null },
        ],
      });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText(/admin-user/)).toBeInTheDocument();
    });

    it("displays reason in quotes when available", () => {
      const policy = buildMockPolicy({
        timeline: [
          { timestamp: "2026-03-04T10:00:00Z", action: "test", operator: null, reason: "This is the reason" },
        ],
      });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText(/This is the reason/)).toBeInTheDocument();
    });

    it("shows 'No events recorded' when timeline is empty", () => {
      const policy = buildMockPolicy({ timeline: [] });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText("No events recorded.")).toBeInTheDocument();
    });

    it("renders only last 5 events", () => {
      const policy = buildMockPolicy({
        timeline: [
          { timestamp: "2026-03-04T10:00:00Z", action: "event-1", operator: null, reason: null },
          { timestamp: "2026-03-04T09:00:00Z", action: "event-2", operator: null, reason: null },
          { timestamp: "2026-03-04T08:00:00Z", action: "event-3", operator: null, reason: null },
          { timestamp: "2026-03-04T07:00:00Z", action: "event-4", operator: null, reason: null },
          { timestamp: "2026-03-04T06:00:00Z", action: "event-5", operator: null, reason: null },
          { timestamp: "2026-03-04T05:00:00Z", action: "event-6", operator: null, reason: null },
        ],
      });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText("event-1")).toBeInTheDocument();
      expect(screen.getByText("event-5")).toBeInTheDocument();
      expect(screen.queryByText("event-6")).not.toBeInTheDocument();
    });
  });

  describe("Metrics Section", () => {
    it("displays total evaluations", () => {
      const policy = buildMockPolicy({
        metrics: { total_evaluations: 1000, success_rate: 0.95, avg_latency_ms: 50, error_rate: 0.01 },
      });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText("1,000")).toBeInTheDocument();
    });

    it("displays success rate as percentage", () => {
      const policy = buildMockPolicy({
        metrics: { total_evaluations: 100, success_rate: 0.96, avg_latency_ms: 50, error_rate: 0.01 },
      });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText("96.0%")).toBeInTheDocument();
    });

    it("success rate is green when >= 95%", () => {
      const policy = buildMockPolicy({
        metrics: { total_evaluations: 100, success_rate: 0.96, avg_latency_ms: 50, error_rate: 0.01 },
      });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      const successRate = screen.getByText("96.0%");
      expect(successRate).toHaveClass("text-green-600");
    });

    it("success rate is amber when between 90% and 95%", () => {
      const policy = buildMockPolicy({
        metrics: { total_evaluations: 100, success_rate: 0.92, avg_latency_ms: 50, error_rate: 0.01 },
      });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      const successRate = screen.getByText("92.0%");
      expect(successRate).toHaveClass("text-amber-600");
    });

    it("success rate is red when < 90%", () => {
      const policy = buildMockPolicy({
        metrics: { total_evaluations: 100, success_rate: 0.85, avg_latency_ms: 50, error_rate: 0.01 },
      });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      const successRate = screen.getByText("85.0%");
      expect(successRate).toHaveClass("text-red-600");
    });

    it("displays average latency", () => {
      const policy = buildMockPolicy({
        metrics: { total_evaluations: 100, success_rate: 0.95, avg_latency_ms: 45.7, error_rate: 0.01 },
      });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText("46ms")).toBeInTheDocument();
    });

    it("displays error rate as percentage", () => {
      const policy = buildMockPolicy({
        metrics: { total_evaluations: 100, success_rate: 0.95, avg_latency_ms: 50, error_rate: 0.005 },
      });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText("0.50%")).toBeInTheDocument();
    });

    it("error rate is green when <= 1%", () => {
      const policy = buildMockPolicy({
        metrics: { total_evaluations: 100, success_rate: 0.95, avg_latency_ms: 50, error_rate: 0.005 },
      });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      const errorRate = screen.getByText("0.50%");
      expect(errorRate).toHaveClass("text-green-600");
    });

    it("error rate is amber when between 1% and 5%", () => {
      const policy = buildMockPolicy({
        metrics: { total_evaluations: 100, success_rate: 0.95, avg_latency_ms: 50, error_rate: 0.03 },
      });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      const errorRate = screen.getByText("3.00%");
      expect(errorRate).toHaveClass("text-amber-600");
    });

    it("error rate is red when > 5%", () => {
      const policy = buildMockPolicy({
        metrics: { total_evaluations: 100, success_rate: 0.95, avg_latency_ms: 50, error_rate: 0.08 },
      });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      const errorRate = screen.getByText("8.00%");
      expect(errorRate).toHaveClass("text-red-600");
    });
  });

  describe("Rollback Notice", () => {
    it("shows rollback available notice when can_rollback is true", () => {
      const policy = buildMockPolicy({ can_rollback: true });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByText("Rollback Available")).toBeInTheDocument();
    });

    it("does not show rollback notice when can_rollback is false", () => {
      const policy = buildMockPolicy({ can_rollback: false });
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.queryByText("Rollback Available")).not.toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has role='region' for policy details", () => {
      const policy = buildMockPolicy();
      render(<PolicyDetail policy={policy} isExpanded={true} />);

      expect(screen.getByRole("region", { name: "Policy details for exp-001" })).toBeInTheDocument();
    });
  });
});
