import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import NavigationPanel from "./NavigationPanel";

vi.mock("../../api/client", () => ({
  fetchJson: vi.fn(async (endpoint: string) => {
    if (endpoint === "/api/v2/brands") {
      return { brands: [{ brand_id: "brand-1", name: "Acme" }] };
    }
    if (endpoint.startsWith("/api/v2/projects")) {
      return {
        projects: [{ project_id: "project-1", brand_id: "brand-1", name: "Launch Sprint" }],
      };
    }
    if (endpoint.startsWith("/api/v2/threads")) {
      return {
        threads: [
          {
            thread_id: "thread-1",
            project_id: "project-1",
            brand_id: "brand-1",
            title: "Lancamento editorial",
            modes: ["content_calendar", "landing_page"],
          },
        ],
      };
    }
    throw new Error(`Unexpected endpoint: ${endpoint}`);
  }),
  postJson: vi.fn(),
  patchJson: vi.fn(),
}));

describe("NavigationPanel", () => {
  it("renders reduced context sections for mode, versions and job context", async () => {
    render(
      <NavigationPanel
        activeBrandId="brand-1"
        activeProjectId="project-1"
        activeThreadId="thread-1"
        devMode={false}
        onSelectBrand={() => {}}
        onSelectProject={() => {}}
        onSelectThread={() => {}}
      />
    );

    expect(await screen.findByRole("heading", { name: "Modo" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Versoes" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Contexto do Job" })).toBeInTheDocument();
  });
});
