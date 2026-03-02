/**
 * Unified Workspace Layout State Management
 * 
 * Provides centralized state management for the v37 3-column unified workspace:
 * - Left: Task steps + Operational queue (hybrid)
 * - Center: Editor + Timeline (split)
 * - Right: Next best actions + Insights/Alerts (hybrid)
 */

export type ColumnId = "left" | "center" | "right";
export type SectionId = "execution" | "queue" | "insights" | "settings";

export interface ColumnConfig {
  id: ColumnId;
  title: string;
  width: number | "flex";
  minWidth: number;
  maxWidth?: number;
  visible: boolean;
  components: string[];
  collapsible: boolean;
}

export interface UnifiedLayoutState {
  columns: ColumnConfig[];
  leftCollapsed: boolean;
  rightCollapsed: boolean;
  activeSection: SectionId;
  isMobile: boolean;
  isTablet: boolean;
}

export interface LayoutOptions {
  activeSection?: SectionId;
  isMobile?: boolean;
  isTablet?: boolean;
}

export const DEFAULT_COLUMN_CONFIG: {
  left: ColumnConfig;
  center: ColumnConfig;
  right: ColumnConfig;
  breakpoints: { mobile: number; tablet: number };
} = {
  left: {
    id: "left",
    title: "Etapas & Fila",
    width: 280,
    minWidth: 240,
    maxWidth: 360,
    visible: true,
    components: ["taskRail", "operationalQueue", "stepNavigation"],
    collapsible: true,
  },
  center: {
    id: "center",
    title: "Execução",
    width: "flex",
    minWidth: 400,
    visible: true,
    components: ["editor", "timeline", "primaryAction"],
    collapsible: false,
  },
  right: {
    id: "right",
    title: "Ações & Insights",
    width: 320,
    minWidth: 280,
    maxWidth: 400,
    visible: true,
    components: ["nextBestActions", "insights", "alerts", "roiCards"],
    collapsible: true,
  },
  breakpoints: {
    mobile: 768,
    tablet: 1024,
  },
};

/**
 * Creates the initial unified layout state
 */
export function createUnifiedLayoutState(options: LayoutOptions = {}): UnifiedLayoutState {
  const { activeSection = "execution", isMobile = false, isTablet = false } = options;

  return {
    columns: [
      { ...DEFAULT_COLUMN_CONFIG.left },
      { ...DEFAULT_COLUMN_CONFIG.center },
      { ...DEFAULT_COLUMN_CONFIG.right },
    ],
    leftCollapsed: false,
    rightCollapsed: false,
    activeSection,
    isMobile,
    isTablet,
  };
}

/**
 * Toggle left column visibility
 */
export function toggleLeftColumn(state: UnifiedLayoutState): UnifiedLayoutState {
  const newCollapsed = !state.leftCollapsed;
  return {
    ...state,
    leftCollapsed: newCollapsed,
    columns: state.columns.map((c) =>
      c.id === "left" ? { ...c, visible: !newCollapsed } : c
    ),
  };
}

/**
 * Toggle right column visibility
 */
export function toggleRightColumn(state: UnifiedLayoutState): UnifiedLayoutState {
  const newCollapsed = !state.rightCollapsed;
  return {
    ...state,
    rightCollapsed: newCollapsed,
    columns: state.columns.map((c) =>
      c.id === "right" ? { ...c, visible: !newCollapsed } : c
    ),
  };
}

/**
 * Set active section
 */
export function setActiveSection(
  state: UnifiedLayoutState,
  section: SectionId
): UnifiedLayoutState {
  return {
    ...state,
    activeSection: section,
  };
}

/**
 * Update column width
 */
export function setColumnWidth(
  state: UnifiedLayoutState,
  columnId: ColumnId,
  width: number | "flex"
): UnifiedLayoutState {
  return {
    ...state,
    columns: state.columns.map((c) =>
      c.id === columnId ? { ...c, width } : c
    ),
  };
}

/**
 * Check if layout is in compact mode (mobile/tablet)
 */
export function isCompactMode(state: UnifiedLayoutState): boolean {
  return state.isMobile || state.isTablet;
}

/**
 * Get visible columns count
 */
export function getVisibleColumnsCount(state: UnifiedLayoutState): number {
  return state.columns.filter((c) => c.visible).length;
}

/**
 * Calculate effective widths for CSS grid
 */
export function getGridTemplateColumns(state: UnifiedLayoutState): string {
  if (state.isMobile) {
    // Mobile: single column, show only active
    return "1fr";
  }

  const widths = state.columns
    .filter((c) => c.visible)
    .map((c) => (c.width === "flex" ? "1fr" : `${c.width}px`));

  return widths.join(" ");
}
