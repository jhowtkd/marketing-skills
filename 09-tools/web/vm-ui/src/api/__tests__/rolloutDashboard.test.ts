/**
 * Tests for rolloutDashboard API client
 */

import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import {
  fetchRolloutDashboard,
  approvePromotion,
  rejectPromotion,
  manualRollback,
  trackRolloutDashboardViewed,
  trackApprovalAction,
} from "../rolloutDashboard";

// Mock the client module
const mockFetchJson = vi.fn();
const mockPostJson = vi.fn();

vi.mock("../client", () => ({
  fetchJson: (...args: unknown[]) => mockFetchJson(...args),
  postJson: (...args: unknown[]) => mockPostJson(...args),
}));

describe("rolloutDashboard API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({}),
    });
  });

  describe("fetchRolloutDashboard", () => {
    it("fetches rollout dashboard data", async () => {
      const mockResponse = {
        policies: [
          {
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
            timeline: [],
            metrics: {
              total_evaluations: 150,
              success_rate: 0.96,
              avg_latency_ms: 45,
              error_rate: 0.005,
            },
            can_rollback: false,
          },
        ],
        updated_at: "2026-03-04T10:00:00Z",
      };
      mockFetchJson.mockResolvedValue(mockResponse);

      const result = await fetchRolloutDashboard();

      expect(mockFetchJson).toHaveBeenCalledWith(
        "/api/v2/onboarding/rollout-dashboard"
      );
      expect(result).toEqual(mockResponse.policies);
    });

    it("returns empty array when policies is undefined", async () => {
      mockFetchJson.mockResolvedValue({});

      const result = await fetchRolloutDashboard();

      expect(result).toEqual([]);
    });

    it("propagates fetch errors", async () => {
      mockFetchJson.mockRejectedValue(new Error("Network error"));

      await expect(fetchRolloutDashboard()).rejects.toThrow("Network error");
    });
  });

  describe("approvePromotion", () => {
    it("sends approve request with correct payload", async () => {
      mockPostJson.mockResolvedValue({});

      await approvePromotion("exp-001", "operator-1", "Test approval reason", "variant-A");

      expect(mockPostJson).toHaveBeenCalledWith(
        "/api/v2/onboarding/rollout-policy/exp-001/approve",
        {
          operator_id: "operator-1",
          reason: "Test approval reason",
          variant: "variant-A",
        },
        "approve-promotion"
      );
    });

    it("sends approve request without variant when not provided", async () => {
      mockPostJson.mockResolvedValue({});

      await approvePromotion("exp-001", "operator-1", "Test approval reason");

      expect(mockPostJson).toHaveBeenCalledWith(
        "/api/v2/onboarding/rollout-policy/exp-001/approve",
        {
          operator_id: "operator-1",
          reason: "Test approval reason",
          variant: undefined,
        },
        "approve-promotion"
      );
    });

    it("propagates errors", async () => {
      mockPostJson.mockRejectedValue(new Error("Approval failed"));

      await expect(
        approvePromotion("exp-001", "operator-1", "Test")
      ).rejects.toThrow("Approval failed");
    });
  });

  describe("rejectPromotion", () => {
    it("sends reject request with correct payload", async () => {
      mockPostJson.mockResolvedValue({});

      await rejectPromotion("exp-001", "operator-1", "Test rejection reason");

      expect(mockPostJson).toHaveBeenCalledWith(
        "/api/v2/onboarding/rollout-policy/exp-001/reject",
        {
          operator_id: "operator-1",
          reason: "Test rejection reason",
        },
        "reject-promotion"
      );
    });

    it("propagates errors", async () => {
      mockPostJson.mockRejectedValue(new Error("Rejection failed"));

      await expect(
        rejectPromotion("exp-001", "operator-1", "Test")
      ).rejects.toThrow("Rejection failed");
    });
  });

  describe("manualRollback", () => {
    it("sends rollback request with correct payload", async () => {
      mockPostJson.mockResolvedValue({});

      await manualRollback("exp-001", "operator-1", "Emergency rollback");

      expect(mockPostJson).toHaveBeenCalledWith(
        "/api/v2/onboarding/rollout-policy/exp-001/rollback",
        {
          operator_id: "operator-1",
          reason: "Emergency rollback",
        },
        "manual-rollback"
      );
    });

    it("propagates errors", async () => {
      mockPostJson.mockRejectedValue(new Error("Rollback failed"));

      await expect(
        manualRollback("exp-001", "operator-1", "Test")
      ).rejects.toThrow("Rollback failed");
    });
  });

  describe("trackRolloutDashboardViewed", () => {
    it("sends telemetry event", async () => {
      await trackRolloutDashboardViewed();

      expect(global.fetch).toHaveBeenCalledWith(
        "/api/v2/onboarding/events",
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: expect.stringContaining("rollout_dashboard_viewed"),
        })
      );
    });

    it("does not throw on telemetry failure", async () => {
      (global.fetch as Mock).mockRejectedValue(new Error("Network error"));

      await expect(trackRolloutDashboardViewed()).resolves.not.toThrow();
    });

    it("sends correct timestamp format", async () => {
      const beforeTime = new Date().toISOString();
      await trackRolloutDashboardViewed();
      const afterTime = new Date().toISOString();

      const callArg = (global.fetch as Mock).mock.calls[0][1];
      const body = JSON.parse(callArg.body);

      expect(body.timestamp).toBeDefined();
      expect(body.timestamp >= beforeTime || body.timestamp <= afterTime).toBe(true);
    });
  });

  describe("trackApprovalAction", () => {
    it("sends approved telemetry event", async () => {
      await trackApprovalAction("approved", "exp-001", "operator-1");

      expect(global.fetch).toHaveBeenCalledWith(
        "/api/v2/onboarding/events",
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: expect.stringContaining("rollout_approved"),
        })
      );

      const callArg = (global.fetch as Mock).mock.calls[0][1];
      const body = JSON.parse(callArg.body);

      expect(body.experiment_id).toBe("exp-001");
      expect(body.metadata.operator_id).toBe("operator-1");
    });

    it("sends rejected telemetry event", async () => {
      await trackApprovalAction("rejected", "exp-001", "operator-1");

      const callArg = (global.fetch as Mock).mock.calls[0][1];
      const body = JSON.parse(callArg.body);

      expect(body.event).toBe("rollout_rejected");
    });

    it("sends rollback telemetry event", async () => {
      await trackApprovalAction("rollback", "exp-001", "operator-1");

      const callArg = (global.fetch as Mock).mock.calls[0][1];
      const body = JSON.parse(callArg.body);

      expect(body.event).toBe("rollout_rollback");
    });

    it("does not throw on telemetry failure", async () => {
      (global.fetch as Mock).mockRejectedValue(new Error("Network error"));

      await expect(
        trackApprovalAction("approved", "exp-001", "operator-1")
      ).resolves.not.toThrow();
    });
  });
});
