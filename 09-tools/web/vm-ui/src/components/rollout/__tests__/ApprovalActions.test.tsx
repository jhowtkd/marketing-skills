/**
 * Tests for ApprovalActions component
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ApprovalActions } from "../ApprovalActions";
import type { RolloutMode, RolloutStatus } from "../../../api/rolloutDashboard";

describe("ApprovalActions", () => {
  const defaultProps = {
    mode: "SUPERVISED" as RolloutMode,
    status: "pending_review" as RolloutStatus,
    canRollback: false,
    onApprove: vi.fn(),
    onReject: vi.fn(),
    onRollback: vi.fn(),
    disabled: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Approve/Reject Buttons", () => {
    it("shows approve and reject buttons for SUPERVISED mode with pending_review", () => {
      render(<ApprovalActions {...defaultProps} />);

      expect(screen.getByText("Approve Promotion")).toBeInTheDocument();
      expect(screen.getByText("Reject Promotion")).toBeInTheDocument();
    });

    it("does not show approve/reject for AUTOMATIC mode", () => {
      render(<ApprovalActions {...defaultProps} mode="AUTOMATIC" status="pending_review" />);

      expect(screen.queryByText("Approve Promotion")).not.toBeInTheDocument();
      expect(screen.queryByText("Reject Promotion")).not.toBeInTheDocument();
    });

    it("does not show approve/reject for SHADOW mode", () => {
      render(<ApprovalActions {...defaultProps} mode="SHADOW" status="pending_review" />);

      expect(screen.queryByText("Approve Promotion")).not.toBeInTheDocument();
      expect(screen.queryByText("Reject Promotion")).not.toBeInTheDocument();
    });

    it("does not show approve/reject for non-pending_review status", () => {
      render(<ApprovalActions {...defaultProps} status="promoted" />);

      expect(screen.queryByText("Approve Promotion")).not.toBeInTheDocument();
      expect(screen.queryByText("Reject Promotion")).not.toBeInTheDocument();
    });

    it("calls onApprove when approve button is clicked", () => {
      const onApprove = vi.fn();
      render(<ApprovalActions {...defaultProps} onApprove={onApprove} />);

      fireEvent.click(screen.getByText("Approve Promotion"));

      expect(onApprove).toHaveBeenCalledTimes(1);
    });

    it("calls onReject when reject button is clicked", () => {
      const onReject = vi.fn();
      render(<ApprovalActions {...defaultProps} onReject={onReject} />);

      fireEvent.click(screen.getByText("Reject Promotion"));

      expect(onReject).toHaveBeenCalledTimes(1);
    });
  });

  describe("Rollback Button", () => {
    it("shows rollback button when canRollback is true", () => {
      render(<ApprovalActions {...defaultProps} canRollback={true} />);

      expect(screen.getByText("Force Rollback")).toBeInTheDocument();
    });

    it("shows rollback button for promoted status", () => {
      render(<ApprovalActions {...defaultProps} status="promoted" canRollback={false} />);

      expect(screen.getByText("Force Rollback")).toBeInTheDocument();
    });

    it("does not show rollback button when neither canRollback nor promoted", () => {
      render(<ApprovalActions {...defaultProps} status="pending_review" canRollback={false} />);

      expect(screen.queryByText("Force Rollback")).not.toBeInTheDocument();
    });

    it("calls onRollback when rollback button is clicked", () => {
      const onRollback = vi.fn();
      render(<ApprovalActions {...defaultProps} canRollback={true} onRollback={onRollback} />);

      fireEvent.click(screen.getByText("Force Rollback"));

      expect(onRollback).toHaveBeenCalledTimes(1);
    });
  });

  describe("No Actions Available", () => {
    it("shows 'No actions available' when no actions are available", () => {
      render(
        <ApprovalActions
          {...defaultProps}
          mode="SHADOW"
          status="evaluating"
          canRollback={false}
        />
      );

      expect(screen.getByText("No actions available")).toBeInTheDocument();
    });
  });

  describe("Disabled State", () => {
    it("disables approve button when disabled prop is true", () => {
      render(<ApprovalActions {...defaultProps} disabled={true} />);

      expect(screen.getByText("Approve Promotion")).toBeDisabled();
    });

    it("disables reject button when disabled prop is true", () => {
      render(<ApprovalActions {...defaultProps} disabled={true} />);

      expect(screen.getByText("Reject Promotion")).toBeDisabled();
    });

    it("disables rollback button when disabled prop is true", () => {
      render(<ApprovalActions {...defaultProps} canRollback={true} disabled={true} />);

      expect(screen.getByText("Force Rollback")).toBeDisabled();
    });
  });

  describe("Button Styling", () => {
    it("approve button has green styling", () => {
      render(<ApprovalActions {...defaultProps} />);

      const button = screen.getByText("Approve Promotion");
      expect(button).toHaveClass("bg-green-600");
    });

    it("reject button has amber/orange styling", () => {
      render(<ApprovalActions {...defaultProps} />);

      const button = screen.getByText("Reject Promotion");
      expect(button).toHaveClass("bg-amber-600");
    });

    it("rollback button has red styling", () => {
      render(<ApprovalActions {...defaultProps} canRollback={true} />);

      const button = screen.getByText("Force Rollback");
      expect(button).toHaveClass("bg-red-600");
    });
  });

  describe("Accessibility", () => {
    it("has aria-label for approve button", () => {
      render(<ApprovalActions {...defaultProps} />);

      expect(screen.getByLabelText("Approve promotion to production")).toBeInTheDocument();
    });

    it("has aria-label for reject button", () => {
      render(<ApprovalActions {...defaultProps} />);

      expect(screen.getByLabelText("Reject promotion")).toBeInTheDocument();
    });

    it("has aria-label for rollback button", () => {
      render(<ApprovalActions {...defaultProps} canRollback={true} />);

      expect(screen.getByLabelText("Force rollback to previous version")).toBeInTheDocument();
    });

    it("container has role='group'", () => {
      render(<ApprovalActions {...defaultProps} />);

      expect(screen.getByRole("group", { name: "Approval actions" })).toBeInTheDocument();
    });

    it("approve button has focus ring classes", () => {
      render(<ApprovalActions {...defaultProps} />);

      const button = screen.getByText("Approve Promotion");
      expect(button).toHaveClass("focus:ring-2");
      expect(button).toHaveClass("focus:ring-green-500");
    });
  });

  describe("Icons", () => {
    it("approve button has checkmark icon", () => {
      render(<ApprovalActions {...defaultProps} />);

      const button = screen.getByText("Approve Promotion");
      const svg = button.querySelector("svg");
      expect(svg).toBeInTheDocument();
    });

    it("reject button has X icon", () => {
      render(<ApprovalActions {...defaultProps} />);

      const button = screen.getByText("Reject Promotion");
      const svg = button.querySelector("svg");
      expect(svg).toBeInTheDocument();
    });

    it("rollback button has undo icon", () => {
      render(<ApprovalActions {...defaultProps} canRollback={true} />);

      const button = screen.getByText("Force Rollback");
      const svg = button.querySelector("svg");
      expect(svg).toBeInTheDocument();
    });

    it("icons have aria-hidden", () => {
      render(<ApprovalActions {...defaultProps} />);

      const approveButton = screen.getByText("Approve Promotion");
      const svg = approveButton.querySelector("svg");
      expect(svg).toHaveAttribute("aria-hidden", "true");
    });
  });
});
