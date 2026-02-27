import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import GuidedRegenerateModal from "./GuidedRegenerateModal";

describe("GuidedRegenerateModal", () => {
  it("allows selecting presets", () => {
    render(
      <GuidedRegenerateModal
        isOpen
        baseRequest="Plano de lancamento"
        weakPoints={["CTA fraco"]}
        onClose={() => {}}
        onSubmit={() => {}}
      />
    );

    const preset = screen.getByLabelText("Mais profundo");
    fireEvent.click(preset);

    expect((preset as HTMLInputElement).checked).toBe(true);
  });

  it("submits consolidated payload", () => {
    const onSubmit = vi.fn();
    render(
      <GuidedRegenerateModal
        isOpen
        baseRequest="Plano de lancamento"
        weakPoints={["CTA fraco"]}
        onClose={() => {}}
        onSubmit={onSubmit}
      />
    );

    fireEvent.click(screen.getByLabelText("Mais persuasivo"));
    fireEvent.change(screen.getByLabelText("Guia adicional"), {
      target: { value: "focar em ICP B2B" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Gerar versao guiada" }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit.mock.calls[0][0].presets).toEqual(["mais_persuasivo"]);
    expect(onSubmit.mock.calls[0][0].requestText).toContain("Plano de lancamento");
    expect(onSubmit.mock.calls[0][0].requestText).toContain("CTA fraco");
    expect(onSubmit.mock.calls[0][0].requestText).toContain("ICP B2B");
  });
});
