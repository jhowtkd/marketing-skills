import { describe, it, expect } from "vitest";
import {
  createUnifiedLayoutState,
  type UnifiedLayoutState,
  type ColumnConfig,
  DEFAULT_COLUMN_CONFIG,
} from "./unifiedLayout";

describe("unifiedLayout", () => {
  describe("createUnifiedLayoutState", () => {
    it("should create initial state with 3-column layout", () => {
      const state = createUnifiedLayoutState();

      expect(state.columns).toHaveLength(3);
      expect(state.columns[0].id).toBe("left");
      expect(state.columns[1].id).toBe("center");
      expect(state.columns[2].id).toBe("right");
    });

    it("should have correct default widths", () => {
      const state = createUnifiedLayoutState();

      expect(state.columns[0].width).toBe(280); // left: 280px
      expect(state.columns[1].width).toBe("flex"); // center: flex
      expect(state.columns[2].width).toBe(320); // right: 320px
    });

    it("should have correct default visibility", () => {
      const state = createUnifiedLayoutState();

      expect(state.columns[0].visible).toBe(true);
      expect(state.columns[1].visible).toBe(true);
      expect(state.columns[2].visible).toBe(true);
    });

    it("should initialize with collapsed state false", () => {
      const state = createUnifiedLayoutState();

      expect(state.leftCollapsed).toBe(false);
      expect(state.rightCollapsed).toBe(false);
    });

    it("should initialize active section as execution", () => {
      const state = createUnifiedLayoutState();

      expect(state.activeSection).toBe("execution");
    });

    it("should accept custom initial section", () => {
      const state = createUnifiedLayoutState({ activeSection: "queue" });

      expect(state.activeSection).toBe("queue");
    });
  });

  describe("column configuration", () => {
    it("should have correct left column config", () => {
      const left = DEFAULT_COLUMN_CONFIG.left;

      expect(left.id).toBe("left");
      expect(left.title).toBe("Etapas & Fila");
      expect(left.components).toContain("taskRail");
      expect(left.components).toContain("operationalQueue");
    });

    it("should have correct center column config", () => {
      const center = DEFAULT_COLUMN_CONFIG.center;

      expect(center.id).toBe("center");
      expect(center.title).toBe("Execução");
      expect(center.components).toContain("editor");
      expect(center.components).toContain("timeline");
    });

    it("should have correct right column config", () => {
      const right = DEFAULT_COLUMN_CONFIG.right;

      expect(right.id).toBe("right");
      expect(right.title).toBe("Ações & Insights");
      expect(right.components).toContain("nextBestActions");
      expect(right.components).toContain("insights");
      expect(right.components).toContain("alerts");
    });
  });

  describe("responsive breakpoints", () => {
    it("should define mobile breakpoint", () => {
      expect(DEFAULT_COLUMN_CONFIG.breakpoints.mobile).toBe(768);
    });

    it("should define tablet breakpoint", () => {
      expect(DEFAULT_COLUMN_CONFIG.breakpoints.tablet).toBe(1024);
    });
  });

  describe("state transitions", () => {
    it("should support toggling left column", () => {
      const state = createUnifiedLayoutState();
      const toggled = {
        ...state,
        leftCollapsed: !state.leftCollapsed,
        columns: state.columns.map((c) =>
          c.id === "left" ? { ...c, visible: !c.visible } : c
        ),
      };

      expect(toggled.leftCollapsed).toBe(true);
      expect(toggled.columns[0].visible).toBe(false);
    });

    it("should support toggling right column", () => {
      const state = createUnifiedLayoutState();
      const toggled = {
        ...state,
        rightCollapsed: !state.rightCollapsed,
        columns: state.columns.map((c) =>
          c.id === "right" ? { ...c, visible: !c.visible } : c
        ),
      };

      expect(toggled.rightCollapsed).toBe(true);
      expect(toggled.columns[2].visible).toBe(false);
    });

    it("should support changing active section", () => {
      const state = createUnifiedLayoutState();
      const changed = { ...state, activeSection: "insights" as const };

      expect(changed.activeSection).toBe("insights");
    });
  });
});
