/**
 * Tests for RolloutDashboard page
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { RolloutDashboard } from "../../../pages/RolloutDashboard";

// Mock the API module
const mockFetchRolloutDashboard = vi.fn();
const mockApprovePromotion = vi.fn();
const mockRejectPromotion = vi.fn();
const mockManualRollback = vi.fn();
const mockTrackRolloutDashboardViewed = vi.fn();
const mockTrackApprovalAction = vi.fn();

vi.mock("../../../api/rolloutDashboard", () => ({
  fetchRolloutDashboard: (...args: unknown[]) => mockFetchRolloutDashboard(...args),
  approvePromotion: (...args: unknown[]) => mockApprovePromotion(...args),
  rejectPromotion: (...args: unknown[]) => mockRejectPromotion(...args),
  manualRollback: (...args: unknown[]) => mockManualRollback(...args),
  trackRolloutDashboardViewed: (...args: unknown[]) =>
    mockTrackRolloutDashboardViewed(...args),
  trackApprovalAction: (...args: unknown[]) => mockTrackApprovalAction(...args),
}));

// Mock timer for auto-refresh tests
vi.useFakeTimers({ shouldAdvanceTime: true });

function buildMockPolicy(overrides: Record<string, unknown> = {}) {
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

function buildMockPolicies() {
  return [
    buildMockPolicy({
      experiment_id: "exp-001",
      mode: "SUPERVISED",
      status: "pending_review",
      active_variant: "variant-A",
    }),
    buildMockPolicy({
      experiment_id: "exp-002",
      mode: "AUTOMATIC",
      status: "promoted",
      active_variant: "variant-B",
      can_rollback: true,
    }),
    buildMockPolicy({
      experiment_id: "exp-003",
      mode: "SHADOW",
      status: "evaluating",
      active_variant: "variant-C",
    }),
    buildMockPolicy({
      experiment_id: "exp-004",
      mode: "SUPERVISED",
      status: "blocked",
      active_variant: "variant-D",
    }),
    buildMockPolicy({
      experiment_id: "exp-005",
      mode: "SUPERVISED",
      status: "rolled_back",
      active_variant: "variant-E",
      can_rollback: false,
    }),
  ];
}

describe("RolloutDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchRolloutDashboard.mockResolvedValue(buildMockPolicies());
    mockTrackRolloutDashboardViewed.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  describe("Initial Load", () => {
    it("renders loading state initially", () => {
      mockFetchRolloutDashboard.mockImplementation(() => new Promise(() => {}));
      render(<RolloutDashboard />);

      expect(screen.getByText("Loading rollout policies...")).toBeInTheDocument();
    });

    it("fetches and displays policies on mount", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("exp-001")).toBeInTheDocument();
      });

      expect(screen.getByText("exp-002")).toBeInTheDocument();
      expect(screen.getByText("exp-003")).toBeInTheDocument();
    });

    it("tracks dashboard view on mount", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(mockTrackRolloutDashboardViewed).toHaveBeenCalledTimes(1);
      });
    });

    it("displays error state when fetch fails", async () => {
      mockFetchRolloutDashboard.mockRejectedValue(new Error("Network error"));
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("Failed to Load Dashboard")).toBeInTheDocument();
      });

      expect(screen.getByText("Network error")).toBeInTheDocument();
    });

    it("allows retry after error", async () => {
      mockFetchRolloutDashboard.mockRejectedValue(new Error("Network error"));
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("Try Again")).toBeInTheDocument();
      });

      mockFetchRolloutDashboard.mockResolvedValue(buildMockPolicies());
      fireEvent.click(screen.getByText("Try Again"));

      await waitFor(() => {
        expect(screen.getByText("exp-001")).toBeInTheDocument();
      });
    });
  });

  describe("Empty State", () => {
    it("displays empty state when no policies exist", async () => {
      mockFetchRolloutDashboard.mockResolvedValue([]);
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("No Experiments Found")).toBeInTheDocument();
      });

      expect(
        screen.getByText("There are no experiments with rollout policies configured yet.")
      ).toBeInTheDocument();
    });
  });

  describe("Table Rendering", () => {
    it("renders all required columns", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("Experiment ID")).toBeInTheDocument();
      });

      expect(screen.getByText("Active Variant")).toBeInTheDocument();
      expect(screen.getByText("Mode")).toBeInTheDocument();
      expect(screen.getByText("Status")).toBeInTheDocument();
      expect(screen.getByText("Last Evaluation")).toBeInTheDocument();
      expect(screen.getByText("Actions")).toBeInTheDocument();
      expect(screen.getByText("Details")).toBeInTheDocument();
    });

    it("displays policy data correctly", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("exp-001")).toBeInTheDocument();
      });

      // Get the specific row for exp-001 and check within it
      const row = screen.getByText("exp-001").closest("tr");
      expect(row).toBeTruthy();
      expect(within(row!).getByText("variant-A")).toBeInTheDocument();
      expect(within(row!).getByText("SUPERVISED")).toBeInTheDocument();
      expect(within(row!).getByText("Pending Review")).toBeInTheDocument();
    });

    it("displays null variant as em dash", async () => {
      // Mock with null variant for exp-003
      mockFetchRolloutDashboard.mockResolvedValue([
        buildMockPolicy({ experiment_id: "exp-003", active_variant: null, mode: "SHADOW", status: "evaluating" }),
      ]);
      
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("exp-003")).toBeInTheDocument();
      });

      const row = screen.getByText("exp-003").closest("tr");
      expect(row).toBeTruthy();
      expect(within(row!).getByText("—")).toBeInTheDocument();
    });
  });

  describe("Status Badges", () => {
    it("renders promoted status with green badge", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("Promoted")).toBeInTheDocument();
      });

      const badge = screen.getByText("Promoted").closest("[role='status']");
      expect(badge).toHaveClass("bg-green-100");
    });

    it("renders blocked status with red badge", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("Blocked")).toBeInTheDocument();
      });

      const badge = screen.getByText("Blocked").closest("[role='status']");
      expect(badge).toHaveClass("bg-red-100");
    });

    it("renders rolled_back status with orange badge", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("Rolled Back")).toBeInTheDocument();
      });

      const badge = screen.getByText("Rolled Back").closest("[role='status']");
      expect(badge).toHaveClass("bg-orange-100");
    });

    it("renders evaluating status with loading spinner", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("Evaluating")).toBeInTheDocument();
      });

      const badge = screen.getByText("Evaluating").closest("[role='status']");
      expect(badge).toHaveClass("bg-blue-100");
    });
  });

  describe("Approval Actions", () => {
    it("shows approve/reject buttons for supervised mode with pending review", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("exp-001")).toBeInTheDocument();
      });

      const row = screen.getByText("exp-001").closest("tr");
      expect(row).toBeTruthy();
      expect(within(row!).getByText("Approve Promotion")).toBeInTheDocument();
      expect(within(row!).getByText("Reject Promotion")).toBeInTheDocument();
    });

    it("shows rollback button for promoted experiments", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("exp-002")).toBeInTheDocument();
      });

      const row = screen.getByText("exp-002").closest("tr");
      expect(row).toBeTruthy();
      expect(within(row!).getByText("Force Rollback")).toBeInTheDocument();
    });

    it("does not show approve/reject for automatic mode", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("exp-002")).toBeInTheDocument();
      });

      const row = screen.getByText("exp-002").closest("tr");
      expect(row).toBeTruthy();
      expect(within(row!).queryByText("Approve Promotion")).not.toBeInTheDocument();
      expect(within(row!).queryByText("Reject Promotion")).not.toBeInTheDocument();
    });

    it("shows no actions available for shadow mode experiments", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("exp-003")).toBeInTheDocument();
      });

      const row = screen.getByText("exp-003").closest("tr");
      expect(row).toBeTruthy();
      expect(within(row!).getByText("No actions available")).toBeInTheDocument();
    });
  });

  describe("Expandable Details", () => {
    it("expands row when details button is clicked", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("exp-001")).toBeInTheDocument();
      });

      const expandButtons = screen.getAllByLabelText("Show details");
      fireEvent.click(expandButtons[0]);

      expect(screen.getByText("Policy Configuration")).toBeInTheDocument();
      expect(screen.getByText("Recent Events")).toBeInTheDocument();
      expect(screen.getByText("Current Metrics")).toBeInTheDocument();
    });

    it("collapses row when details button is clicked again", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("exp-001")).toBeInTheDocument();
      });

      const expandButtons = screen.getAllByLabelText("Show details");
      fireEvent.click(expandButtons[0]);
      expect(screen.getByText("Policy Configuration")).toBeInTheDocument();

      fireEvent.click(screen.getByLabelText("Hide details"));
      expect(screen.queryByText("Policy Configuration")).not.toBeInTheDocument();
    });

    it("displays timeline events in expanded view", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("exp-001")).toBeInTheDocument();
      });

      const expandButtons = screen.getAllByLabelText("Show details");
      fireEvent.click(expandButtons[0]);

      expect(screen.getByText("evaluation_completed")).toBeInTheDocument();
      expect(screen.getByText("evaluation_started")).toBeInTheDocument();
    });

    it("displays metrics in expanded view", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("exp-001")).toBeInTheDocument();
      });

      const expandButtons = screen.getAllByLabelText("Show details");
      fireEvent.click(expandButtons[0]);

      expect(screen.getByText("Total Evaluations")).toBeInTheDocument();
      expect(screen.getByText("150")).toBeInTheDocument();
      expect(screen.getByText("Success Rate")).toBeInTheDocument();
      expect(screen.getByText("96.0%")).toBeInTheDocument();
    });
  });

  describe("Refresh Functionality", () => {
    it("has a refresh button", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("Refresh")).toBeInTheDocument();
      });
    });

    it("refreshes data when refresh button is clicked", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("Refresh")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Refresh"));

      await waitFor(() => {
        expect(mockFetchRolloutDashboard).toHaveBeenCalledTimes(2);
      });
    });

    it("auto-refreshes every 30 seconds", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("exp-001")).toBeInTheDocument();
      });

      // Fast forward 30 seconds
      vi.advanceTimersByTime(30000);

      await waitFor(() => {
        expect(mockFetchRolloutDashboard).toHaveBeenCalledTimes(2);
      });

      // Fast forward another 30 seconds
      vi.advanceTimersByTime(30000);

      await waitFor(() => {
        expect(mockFetchRolloutDashboard).toHaveBeenCalledTimes(3);
      });
    });
  });

  describe("Modal Interactions", () => {
    it("opens approval modal when approve button is clicked", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("Approve Promotion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getAllByText("Approve Promotion")[0]);

      expect(screen.getByText("Confirm Promotion Approval")).toBeInTheDocument();
      expect(screen.getByLabelText("Operator ID *")).toBeInTheDocument();
      expect(screen.getByLabelText("Reason *")).toBeInTheDocument();
    });

    it("opens rejection modal when reject button is clicked", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("Reject Promotion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getAllByText("Reject Promotion")[0]);

      expect(screen.getByText("Confirm Promotion Rejection")).toBeInTheDocument();
    });

    it("opens rollback modal when rollback button is clicked", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("Force Rollback")).toBeInTheDocument();
      });

      fireEvent.click(screen.getAllByText("Force Rollback")[0]);

      expect(screen.getByText("Confirm Manual Rollback")).toBeInTheDocument();
    });

    it("closes modal when cancel is clicked", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("Approve Promotion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getAllByText("Approve Promotion")[0]);
      expect(screen.getByText("Confirm Promotion Approval")).toBeInTheDocument();

      fireEvent.click(screen.getByText("Cancel"));
      expect(screen.queryByText("Confirm Promotion Approval")).not.toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has proper heading structure", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByRole("heading", { name: "Rollout Dashboard" })).toBeInTheDocument();
      });
    });

    it("has accessible status badges", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        const badges = screen.getAllByRole("status");
        expect(badges.length).toBeGreaterThan(0);
      });
    });

    it("modal has proper ARIA attributes when open", async () => {
      render(<RolloutDashboard />);

      await waitFor(() => {
        expect(screen.getByText("Approve Promotion")).toBeInTheDocument();
      });

      fireEvent.click(screen.getAllByText("Approve Promotion")[0]);

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-modal", "true");
      expect(dialog).toHaveAttribute("aria-labelledby", "approval-modal-title");
      expect(dialog).toHaveAttribute("aria-describedby", "approval-modal-description");
    });
  });
});
