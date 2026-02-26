import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./features/navigation/NavigationPanel", () => ({
  default: () => <div>Navigation Panel</div>,
}));

vi.mock("./features/workspace/WorkspacePanel", () => ({
  default: () => <div>Workspace Panel</div>,
}));

vi.mock("./features/inbox/InboxPanel", () => ({
  default: () => <div>Inbox Panel</div>,
}));

describe("App shell", () => {
  it("renders the deliverable-first context bar and three named regions", () => {
    render(<App />);

    expect(screen.getByRole("banner")).toHaveTextContent("VM Studio");
    expect(screen.getByText("Contexto ativo")).toBeInTheDocument();

    const navigationRegion = screen.getByRole("region", { name: "Navegacao do studio" });
    const canvasRegion = screen.getByRole("region", { name: "Canvas do entregavel" });
    const actionRailRegion = screen.getByRole("region", { name: "Action rail da versao" });

    expect(within(navigationRegion).getByText("Navigation Panel")).toBeInTheDocument();
    expect(within(canvasRegion).getByText("Workspace Panel")).toBeInTheDocument();
    expect(within(actionRailRegion).getByText("Inbox Panel")).toBeInTheDocument();
  });
});
