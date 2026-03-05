/**
 * Tests for ApprovalModal component
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ApprovalModal, type ApprovalAction } from "../ApprovalModal";

describe("ApprovalModal", () => {
  const defaultProps = {
    isOpen: true,
    action: "approve" as ApprovalAction,
    experimentId: "exp-001",
    onClose: vi.fn(),
    onSubmit: vi.fn(),
    isSubmitting: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("does not render when isOpen is false", () => {
      render(<ApprovalModal {...defaultProps} isOpen={false} />);

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("renders when isOpen is true", () => {
      render(<ApprovalModal {...defaultProps} />);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("renders correct title for approve action", () => {
      render(<ApprovalModal {...defaultProps} action="approve" />);

      expect(screen.getByText("Confirm Promotion Approval")).toBeInTheDocument();
    });

    it("renders correct title for reject action", () => {
      render(<ApprovalModal {...defaultProps} action="reject" />);

      expect(screen.getByText("Confirm Promotion Rejection")).toBeInTheDocument();
    });

    it("renders correct title for rollback action", () => {
      render(<ApprovalModal {...defaultProps} action="rollback" />);

      expect(screen.getByText("Confirm Manual Rollback")).toBeInTheDocument();
    });

    it("renders correct description for approve action", () => {
      render(<ApprovalModal {...defaultProps} action="approve" />);

      expect(
        screen.getByText(/promote the experiment variant to production/)
      ).toBeInTheDocument();
    });

    it("renders correct description for reject action", () => {
      render(<ApprovalModal {...defaultProps} action="reject" />);

      expect(
        screen.getByText(/reject the promotion and keep the current variant/)
      ).toBeInTheDocument();
    });

    it("renders correct description for rollback action", () => {
      render(<ApprovalModal {...defaultProps} action="rollback" />);

      expect(
        screen.getByText(/immediately rollback the experiment/)
      ).toBeInTheDocument();
    });

    it("renders form fields", () => {
      render(<ApprovalModal {...defaultProps} />);

      expect(screen.getByLabelText(/Operator ID/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Reason/)).toBeInTheDocument();
    });

    it("renders cancel and confirm buttons", () => {
      render(<ApprovalModal {...defaultProps} />);

      expect(screen.getByText("Cancel")).toBeInTheDocument();
      expect(screen.getByText("Approve Promotion")).toBeInTheDocument();
    });
  });

  describe("Form Validation", () => {
    it("confirm button is disabled when form is empty", () => {
      render(<ApprovalModal {...defaultProps} />);

      const confirmButton = screen.getByText("Approve Promotion");
      expect(confirmButton).toBeDisabled();
    });

    it("confirm button is disabled when only operator ID is filled", () => {
      render(<ApprovalModal {...defaultProps} />);

      fireEvent.change(screen.getByLabelText(/Operator ID/), {
        target: { value: "operator-001" },
      });

      const confirmButton = screen.getByText("Approve Promotion");
      expect(confirmButton).toBeDisabled();
    });

    it("confirm button is disabled when reason is too short", () => {
      render(<ApprovalModal {...defaultProps} />);

      fireEvent.change(screen.getByLabelText(/Operator ID/), {
        target: { value: "operator-001" },
      });
      fireEvent.change(screen.getByLabelText(/Reason/), {
        target: { value: "short" },
      });

      const confirmButton = screen.getByText("Approve Promotion");
      expect(confirmButton).toBeDisabled();
    });

    it("confirm button is enabled when both fields are valid", () => {
      render(<ApprovalModal {...defaultProps} />);

      fireEvent.change(screen.getByLabelText(/Operator ID/), {
        target: { value: "operator-001" },
      });
      fireEvent.change(screen.getByLabelText(/Reason/), {
        target: { value: "This is a valid reason with enough characters" },
      });

      const confirmButton = screen.getByText("Approve Promotion");
      expect(confirmButton).not.toBeDisabled();
    });

    it("shows character count for reason field", () => {
      render(<ApprovalModal {...defaultProps} />);

      fireEvent.change(screen.getByLabelText(/Reason/), {
        target: { value: "test" },
      });

      expect(screen.getByText("4/10")).toBeInTheDocument();
    });

    it("shows validation message when reason is too short", () => {
      render(<ApprovalModal {...defaultProps} />);

      fireEvent.change(screen.getByLabelText(/Reason/), {
        target: { value: "short" },
      });

      expect(screen.getByText("Minimum 10 characters required")).toBeInTheDocument();
    });

    it("shows success message when reason meets requirements", () => {
      render(<ApprovalModal {...defaultProps} />);

      fireEvent.change(screen.getByLabelText(/Reason/), {
        target: { value: "This is a valid reason" },
      });

      expect(screen.getByText("Reason meets requirements")).toBeInTheDocument();
    });

    it("marks operator ID as invalid when empty after interaction", () => {
      render(<ApprovalModal {...defaultProps} />);

      const operatorInput = screen.getByLabelText(/Operator ID/);
      fireEvent.change(operatorInput, { target: { value: "test" } });
      fireEvent.change(operatorInput, { target: { value: "" } });

      expect(screen.getByText("Operator ID is required")).toBeInTheDocument();
    });
  });

  describe("Form Submission", () => {
    it("calls onSubmit with form data when confirm is clicked", async () => {
      const onSubmit = vi.fn().mockResolvedValue(undefined);
      render(<ApprovalModal {...defaultProps} onSubmit={onSubmit} />);

      fireEvent.change(screen.getByLabelText(/Operator ID/), {
        target: { value: "operator-001" },
      });
      fireEvent.change(screen.getByLabelText(/Reason/), {
        target: { value: "This is a valid reason with enough characters" },
      });

      fireEvent.click(screen.getByText("Approve Promotion"));

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith({
          operatorId: "operator-001",
          reason: "This is a valid reason with enough characters",
        });
      });
    });

    it("trims whitespace from inputs before submission", async () => {
      const onSubmit = vi.fn().mockResolvedValue(undefined);
      render(<ApprovalModal {...defaultProps} onSubmit={onSubmit} />);

      fireEvent.change(screen.getByLabelText(/Operator ID/), {
        target: { value: "  operator-001  " },
      });
      fireEvent.change(screen.getByLabelText(/Reason/), {
        target: { value: "  This is a valid reason with enough characters  " },
      });

      fireEvent.click(screen.getByText("Approve Promotion"));

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith({
          operatorId: "operator-001",
          reason: "This is a valid reason with enough characters",
        });
      });
    });

    it("does not submit when form is invalid", () => {
      const onSubmit = vi.fn();
      render(<ApprovalModal {...defaultProps} onSubmit={onSubmit} />);

      fireEvent.click(screen.getByText("Approve Promotion"));

      expect(onSubmit).not.toHaveBeenCalled();
    });

    it("displays error message when submission fails", async () => {
      const onSubmit = vi.fn().mockRejectedValue(new Error("Submission failed"));
      render(<ApprovalModal {...defaultProps} onSubmit={onSubmit} />);

      fireEvent.change(screen.getByLabelText(/Operator ID/), {
        target: { value: "operator-001" },
      });
      fireEvent.change(screen.getByLabelText(/Reason/), {
        target: { value: "This is a valid reason with enough characters" },
      });

      fireEvent.click(screen.getByText("Approve Promotion"));

      await waitFor(() => {
        expect(screen.getByText("Submission failed")).toBeInTheDocument();
      });
    });

    it("displays generic error for non-Error rejections", async () => {
      const onSubmit = vi.fn().mockRejectedValue("string error");
      render(<ApprovalModal {...defaultProps} onSubmit={onSubmit} />);

      fireEvent.change(screen.getByLabelText(/Operator ID/), {
        target: { value: "operator-001" },
      });
      fireEvent.change(screen.getByLabelText(/Reason/), {
        target: { value: "This is a valid reason with enough characters" },
      });

      fireEvent.click(screen.getByText("Approve Promotion"));

      await waitFor(() => {
        expect(screen.getByText("An unexpected error occurred")).toBeInTheDocument();
      });
    });
  });

  describe("Cancel/Close Behavior", () => {
    it("calls onClose when cancel button is clicked", () => {
      const onClose = vi.fn();
      render(<ApprovalModal {...defaultProps} onClose={onClose} />);

      fireEvent.click(screen.getByText("Cancel"));

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("clears form when modal is reopened", () => {
      const { rerender } = render(<ApprovalModal {...defaultProps} isOpen={false} />);

      rerender(<ApprovalModal {...defaultProps} isOpen={true} />);

      fireEvent.change(screen.getByLabelText(/Operator ID/), {
        target: { value: "operator-001" },
      });
      fireEvent.change(screen.getByLabelText(/Reason/), {
        target: { value: "This is a valid reason" },
      });

      // Close and reopen
      rerender(<ApprovalModal {...defaultProps} isOpen={false} />);
      rerender(<ApprovalModal {...defaultProps} isOpen={true} />);

      expect(screen.getByLabelText(/Operator ID/)).toHaveValue("");
      expect(screen.getByLabelText(/Reason/)).toHaveValue("");
    });
  });

  describe("Loading State", () => {
    it("disables inputs when submitting", () => {
      render(<ApprovalModal {...defaultProps} isSubmitting={true} />);

      expect(screen.getByLabelText(/Operator ID/)).toBeDisabled();
      expect(screen.getByLabelText(/Reason/)).toBeDisabled();
    });

    it("disables cancel button when submitting", () => {
      render(<ApprovalModal {...defaultProps} isSubmitting={true} />);

      expect(screen.getByText("Cancel")).toBeDisabled();
    });

    it("shows loading spinner in confirm button when submitting", () => {
      render(<ApprovalModal {...defaultProps} isSubmitting={true} />);

      expect(screen.getByText("Processing...")).toBeInTheDocument();
    });

    it("prevents closing modal when submitting", () => {
      const onClose = vi.fn();
      render(<ApprovalModal {...defaultProps} onClose={onClose} isSubmitting={true} />);

      fireEvent.click(screen.getByText("Cancel"));

      expect(onClose).not.toHaveBeenCalled();
    });
  });

  describe("Button Styles", () => {
    it("approve button has green styling", () => {
      render(<ApprovalModal {...defaultProps} action="approve" />);

      fireEvent.change(screen.getByLabelText(/Operator ID/), {
        target: { value: "operator-001" },
      });
      fireEvent.change(screen.getByLabelText(/Reason/), {
        target: { value: "This is a valid reason with enough characters" },
      });

      const button = screen.getByText("Approve Promotion");
      expect(button).toHaveClass("bg-green-600");
    });

    it("reject button has red styling", () => {
      render(<ApprovalModal {...defaultProps} action="reject" />);

      fireEvent.change(screen.getByLabelText(/Operator ID/), {
        target: { value: "operator-001" },
      });
      fireEvent.change(screen.getByLabelText(/Reason/), {
        target: { value: "This is a valid reason with enough characters" },
      });

      const button = screen.getByText("Reject Promotion");
      expect(button).toHaveClass("bg-red-600");
    });

    it("rollback button has red styling", () => {
      render(<ApprovalModal {...defaultProps} action="rollback" />);

      fireEvent.change(screen.getByLabelText(/Operator ID/), {
        target: { value: "operator-001" },
      });
      fireEvent.change(screen.getByLabelText(/Reason/), {
        target: { value: "This is a valid reason with enough characters" },
      });

      const button = screen.getByText("Force Rollback");
      expect(button).toHaveClass("bg-red-600");
    });
  });

  describe("Accessibility", () => {
    it("has proper ARIA attributes on dialog", () => {
      render(<ApprovalModal {...defaultProps} />);

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-modal", "true");
      expect(dialog).toHaveAttribute("aria-labelledby", "approval-modal-title");
      expect(dialog).toHaveAttribute("aria-describedby", "approval-modal-description");
    });

    it("has proper label associations for inputs", () => {
      render(<ApprovalModal {...defaultProps} />);

      const operatorInput = screen.getByLabelText(/Operator ID/);
      expect(operatorInput).toHaveAttribute("id", "operator-id");

      const reasonInput = screen.getByLabelText(/Reason/);
      expect(reasonInput).toHaveAttribute("id", "reason");
    });

    it("marks required fields with aria-required", () => {
      render(<ApprovalModal {...defaultProps} />);

      expect(screen.getByLabelText(/Operator ID/)).toHaveAttribute("aria-required", "true");
      expect(screen.getByLabelText(/Reason/)).toHaveAttribute("aria-required", "true");
    });

    it("updates aria-invalid on invalid operator ID", () => {
      render(<ApprovalModal {...defaultProps} />);

      const operatorInput = screen.getByLabelText(/Operator ID/);
      fireEvent.change(operatorInput, { target: { value: "test" } });
      fireEvent.change(operatorInput, { target: { value: "" } });

      expect(operatorInput).toHaveAttribute("aria-invalid", "true");
    });

    it("error alert has proper role", async () => {
      const onSubmit = vi.fn().mockRejectedValue(new Error("Test error"));
      render(<ApprovalModal {...defaultProps} onSubmit={onSubmit} />);

      fireEvent.change(screen.getByLabelText(/Operator ID/), {
        target: { value: "operator-001" },
      });
      fireEvent.change(screen.getByLabelText(/Reason/), {
        target: { value: "This is a valid reason with enough characters" },
      });

      fireEvent.click(screen.getByText("Approve Promotion"));

      await waitFor(() => {
        const alert = screen.getByRole("alert");
        expect(alert).toBeInTheDocument();
        expect(alert).toHaveAttribute("aria-live", "assertive");
      });
    });
  });
});
