/**
 * Tests for StatusBadge component
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "../StatusBadge";
import type { RolloutStatus } from "../../../api/rolloutDashboard";

describe("StatusBadge", () => {
  describe("Rendering", () => {
    it.each([
      ["promoted", "Promoted"],
      ["blocked", "Blocked"],
      ["rolled_back", "Rolled Back"],
      ["pending_review", "Pending Review"],
      ["evaluating", "Evaluating"],
    ] as [RolloutStatus, string][]){
      ("renders %s status with label '%s'", (status, expectedLabel) => {
        render(<StatusBadge status={status} />);

        expect(screen.getByText(expectedLabel)).toBeInTheDocument();
      });
    }

    it("renders unknown status with the status value as label", () => {
      render(<StatusBadge status={"unknown_status" as RolloutStatus} />);

      expect(screen.getByText("unknown_status")).toBeInTheDocument();
    });
  });

  describe("Styling", () => {
    it("promoted status has green styling", () => {
      render(<StatusBadge status="promoted" />);

      const badge = screen.getByText("Promoted").closest("[role='status']");
      expect(badge).toHaveClass("bg-green-100");
      expect(badge).toHaveClass("text-green-800");
    });

    it("blocked status has red styling", () => {
      render(<StatusBadge status="blocked" />);

      const badge = screen.getByText("Blocked").closest("[role='status']");
      expect(badge).toHaveClass("bg-red-100");
      expect(badge).toHaveClass("text-red-800");
    });

    it("rolled_back status has orange styling", () => {
      render(<StatusBadge status="rolled_back" />);

      const badge = screen.getByText("Rolled Back").closest("[role='status']");
      expect(badge).toHaveClass("bg-orange-100");
      expect(badge).toHaveClass("text-orange-800");
    });

    it("pending_review status has yellow styling", () => {
      render(<StatusBadge status="pending_review" />);

      const badge = screen.getByText("Pending Review").closest("[role='status']");
      expect(badge).toHaveClass("bg-yellow-100");
      expect(badge).toHaveClass("text-yellow-800");
    });

    it("evaluating status has blue styling", () => {
      render(<StatusBadge status="evaluating" />);

      const badge = screen.getByText("Evaluating").closest("[role='status']");
      expect(badge).toHaveClass("bg-blue-100");
      expect(badge).toHaveClass("text-blue-800");
    });

    it("unknown status has gray styling", () => {
      render(<StatusBadge status={"unknown" as RolloutStatus} />);

      const badge = screen.getByText("unknown").closest("[role='status']");
      expect(badge).toHaveClass("bg-gray-100");
      expect(badge).toHaveClass("text-gray-800");
    });

    it("applies custom className when provided", () => {
      render(<StatusBadge status="promoted" className="custom-class" />);

      const badge = screen.getByText("Promoted").closest("[role='status']");
      expect(badge).toHaveClass("custom-class");
    });
  });

  describe("Evaluating State", () => {
    it("shows loading spinner for evaluating status", () => {
      render(<StatusBadge status="evaluating" />);

      const badge = screen.getByText("Evaluating").closest("[role='status']");
      expect(badge?.querySelector("svg")).toBeInTheDocument();
    });

    it("spinner has animation class", () => {
      render(<StatusBadge status="evaluating" />);

      const badge = screen.getByText("Evaluating").closest("[role='status']");
      const spinner = badge?.querySelector("svg");
      expect(spinner).toHaveClass("animate-spin");
    });

    it("spinner has aria-hidden", () => {
      render(<StatusBadge status="evaluating" />);

      const badge = screen.getByText("Evaluating").closest("[role='status']");
      const spinner = badge?.querySelector("svg");
      expect(spinner).toHaveAttribute("aria-hidden", "true");
    });
  });

  describe("Accessibility", () => {
    it("has role='status'", () => {
      render(<StatusBadge status="promoted" />);

      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it.each([
      ["promoted", "Status: Promoted to production"],
      ["blocked", "Status: Blocked due to policy violation"],
      ["rolled_back", "Status: Rolled back to previous version"],
      ["pending_review", "Status: Pending manual review"],
      ["evaluating", "Status: Currently evaluating"],
    ] as [RolloutStatus, string][]){
      ("has correct aria-label for %s status", (status, expectedLabel) => {
        render(<StatusBadge status={status} />);

        expect(screen.getByRole("status")).toHaveAttribute("aria-label", expectedLabel);
      });
    }

    it("has aria-label for unknown status", () => {
      render(<StatusBadge status={"unknown" as RolloutStatus} />);

      expect(screen.getByRole("status")).toHaveAttribute("aria-label", "Status: unknown");
    });
  });
});
