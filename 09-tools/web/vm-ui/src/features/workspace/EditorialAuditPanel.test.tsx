import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { formatAuditEvent, toHumanActorRole, AUDIT_SCOPE_FILTER_LABELS } from "./presentation";
import type { EditorialAuditEvent } from "./useWorkspace";

describe("EditorialAudit presentation helpers", () => {
  describe("formatAuditEvent", () => {
    it("formats global scope event correctly", () => {
      const event: EditorialAuditEvent = {
        event_id: "evt-123",
        event_type: "EditorialGoldenMarked",
        actor_id: "admin-user",
        actor_role: "admin",
        scope: "global",
        run_id: "run-456",
        justification: "Melhor versao ate agora",
        occurred_at: "2026-02-27T10:30:00Z",
      };

      const display = formatAuditEvent(event);

      expect(display.eventId).toBe("evt-123");
      expect(display.scope).toBe("global");
      expect(display.scopeLabel).toBe("Global");
      expect(display.actorId).toBe("admin-user");
      expect(display.actorRole).toBe("admin");
      expect(display.justification).toBe("Melhor versao ate agora");
      expect(display.formattedDate).toContain("27/02/2026");
    });

    it("formats objective scope event with objective_key", () => {
      const event: EditorialAuditEvent = {
        event_id: "evt-789",
        event_type: "EditorialGoldenMarked",
        actor_id: "editor-user",
        actor_role: "editor",
        scope: "objective",
        objective_key: "campaign-q1-launch",
        run_id: "run-abc",
        justification: "Atende todos os criterios",
        occurred_at: "2026-02-27T14:45:00Z",
      };

      const display = formatAuditEvent(event);

      expect(display.scope).toBe("objective");
      expect(display.scopeLabel).toBe("Objetivo");
      expect(display.objectiveKey).toBe("campaign-q1-launch");
    });
  });

  describe("toHumanActorRole", () => {
    it("translates known roles", () => {
      expect(toHumanActorRole("admin")).toBe("Administrador");
      expect(toHumanActorRole("editor")).toBe("Editor");
      expect(toHumanActorRole("viewer")).toBe("Visualizador");
    });

    it("returns original for unknown roles", () => {
      expect(toHumanActorRole("superuser")).toBe("superuser");
    });
  });

  describe("AUDIT_SCOPE_FILTER_LABELS", () => {
    it("has correct labels", () => {
      expect(AUDIT_SCOPE_FILTER_LABELS.all).toBe("Todos");
      expect(AUDIT_SCOPE_FILTER_LABELS.global).toBe("Global");
      expect(AUDIT_SCOPE_FILTER_LABELS.objective).toBe("Objetivo");
    });
  });
});

describe("EditorialAuditPanel integration", () => {
  // Mock component to test the audit UI logic
  function MockAuditPanel({
    events,
    total,
    scopeFilter,
    onScopeChange,
    pagination,
    onPageChange,
  }: {
    events: EditorialAuditEvent[];
    total: number;
    scopeFilter: "all" | "global" | "objective";
    onScopeChange: (scope: "all" | "global" | "objective") => void;
    pagination: { limit: number; offset: number };
    onPageChange: (newOffset: number) => void;
  }) {
    return (
      <div>
        <div data-testid="scope-filters">
          {(["all", "global", "objective"] as const).map((scope) => (
            <button
              key={scope}
              data-testid={`filter-${scope}`}
              data-active={scopeFilter === scope}
              onClick={() => onScopeChange(scope)}
            >
              {AUDIT_SCOPE_FILTER_LABELS[scope]}
            </button>
          ))}
        </div>
        <div data-testid="events-list">
          {events.map((event) => {
            const display = formatAuditEvent(event);
            return (
              <div key={event.event_id} data-testid={`event-${event.event_id}`}>
                <span data-testid="scope">{display.scopeLabel}</span>
                <span data-testid="actor">{display.actorId}</span>
                <span data-testid="role">{toHumanActorRole(display.actorRole)}</span>
                {display.objectiveKey && (
                  <span data-testid="objective">{display.objectiveKey}</span>
                )}
                <span data-testid="justification">{display.justification}</span>
              </div>
            );
          })}
        </div>
        <div data-testid="pagination">
          <button
            data-testid="prev-page"
            disabled={pagination.offset === 0}
            onClick={() => onPageChange(Math.max(0, pagination.offset - pagination.limit))}
          >
            Anterior
          </button>
          <span data-testid="page-info">
            {pagination.offset + 1} - {Math.min(pagination.offset + pagination.limit, total)} de {total}
          </span>
          <button
            data-testid="next-page"
            disabled={pagination.offset + pagination.limit >= total}
            onClick={() => onPageChange(pagination.offset + pagination.limit)}
          >
            Proximo
          </button>
        </div>
      </div>
    );
  }

  it("renders empty state when no events", () => {
    const { container } = render(
      <MockAuditPanel
        events={[]}
        total={0}
        scopeFilter="all"
        onScopeChange={() => {}}
        pagination={{ limit: 20, offset: 0 }}
        onPageChange={() => {}}
      />
    );

    expect(container.querySelector('[data-testid="events-list"]')).toBeEmptyDOMElement();
  });

  it("renders events with correct formatting", () => {
    const events: EditorialAuditEvent[] = [
      {
        event_id: "evt-1",
        event_type: "EditorialGoldenMarked",
        actor_id: "admin-1",
        actor_role: "admin",
        scope: "global",
        run_id: "run-1",
        justification: "Melhor versao",
        occurred_at: "2026-02-27T10:00:00Z",
      },
      {
        event_id: "evt-2",
        event_type: "EditorialGoldenMarked",
        actor_id: "editor-1",
        actor_role: "editor",
        scope: "objective",
        objective_key: "obj-1",
        run_id: "run-2",
        justification: "Bom resultado",
        occurred_at: "2026-02-27T11:00:00Z",
      },
    ];

    render(
      <MockAuditPanel
        events={events}
        total={2}
        scopeFilter="all"
        onScopeChange={() => {}}
        pagination={{ limit: 20, offset: 0 }}
        onPageChange={() => {}}
      />
    );

    expect(screen.getByTestId("event-evt-1")).toBeInTheDocument();
    expect(screen.getByTestId("event-evt-2")).toBeInTheDocument();
    expect(screen.getAllByTestId("scope")[0]).toHaveTextContent("Global");
    expect(screen.getAllByTestId("scope")[1]).toHaveTextContent("Objetivo");
    expect(screen.getByTestId("objective")).toHaveTextContent("obj-1");
  });

  it("calls onScopeChange when filter button clicked", () => {
    const onScopeChange = vi.fn();

    render(
      <MockAuditPanel
        events={[]}
        total={0}
        scopeFilter="all"
        onScopeChange={onScopeChange}
        pagination={{ limit: 20, offset: 0 }}
        onPageChange={() => {}}
      />
    );

    fireEvent.click(screen.getByTestId("filter-global"));
    expect(onScopeChange).toHaveBeenCalledWith("global");
  });

  it("handles pagination correctly", () => {
    const events: EditorialAuditEvent[] = Array.from({ length: 25 }, (_, i) => ({
      event_id: `evt-${i}`,
      event_type: "EditorialGoldenMarked",
      actor_id: `user-${i}`,
      actor_role: "editor",
      scope: "objective",
      run_id: `run-${i}`,
      justification: `Justificativa ${i}`,
      occurred_at: "2026-02-27T10:00:00Z",
    }));

    const onPageChange = vi.fn();

    render(
      <MockAuditPanel
        events={events.slice(0, 20)}
        total={25}
        scopeFilter="all"
        onScopeChange={() => {}}
        pagination={{ limit: 20, offset: 0 }}
        onPageChange={onPageChange}
      />
    );

    // Next page should be enabled
    expect(screen.getByTestId("next-page")).not.toBeDisabled();

    fireEvent.click(screen.getByTestId("next-page"));
    expect(onPageChange).toHaveBeenCalledWith(20);
  });
});
