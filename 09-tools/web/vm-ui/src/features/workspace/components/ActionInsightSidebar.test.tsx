import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ActionInsightSidebar from "./ActionInsightSidebar";
import type { NextAction, InsightCard, AlertItem } from "./ActionInsightSidebar";

describe("ActionInsightSidebar", () => {
  const defaultNextActions: NextAction[] = [
    {
      id: "action-1",
      title: "Aprovar campanha",
      description: "A campanha está pronta para aprovação",
      impact: "high",
      oneClick: true,
      onExecute: vi.fn(),
    },
    {
      id: "action-2",
      title: "Revisar métricas",
      description: "Verifique as métricas de performance",
      impact: "medium",
      oneClick: false,
      onExecute: vi.fn(),
    },
    {
      id: "action-3",
      title: "Ajustar targeting",
      description: "O targeting pode ser otimizado",
      impact: "low",
      oneClick: true,
      onExecute: vi.fn(),
    },
  ];

  const defaultInsights: InsightCard[] = [
    {
      id: "insight-1",
      type: "opportunity",
      title: "Oportunidade detectada",
      message: "Aumento de 15% no engajamento possível",
      metric: "+15%",
      trend: "up",
    },
    {
      id: "insight-2",
      type: "risk",
      title: "Risco identificado",
      message: "Budget próximo do limite",
      metric: "85%",
      trend: "down",
    },
    {
      id: "insight-3",
      type: "info",
      title: "Dica",
      message: "Melhor horário para postar: 14h",
    },
  ];

  const defaultAlerts: AlertItem[] = [
    {
      id: "alert-1",
      severity: "critical",
      title: "Erro na API",
      message: "Falha na conexão com o servidor",
      timestamp: "2026-03-01T10:00:00Z",
    },
    {
      id: "alert-2",
      severity: "warning",
      title: "Performance degradada",
      message: "Tempo de resposta aumentou",
      timestamp: "2026-03-01T09:30:00Z",
    },
  ];

  const defaultProps = {
    nextActions: defaultNextActions,
    insights: defaultInsights,
    alerts: defaultAlerts,
    onActionExecute: vi.fn(),
    onInsightClick: vi.fn(),
    onAlertDismiss: vi.fn(),
  };

  describe("rendering", () => {
    it("renders the sidebar container", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      expect(screen.getByTestId("action-insight-sidebar")).toBeInTheDocument();
    });

    it("renders section title", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      expect(screen.getByText("Ações & Insights")).toBeInTheDocument();
    });

    it("renders next actions section", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      expect(screen.getByText("Próximas Ações")).toBeInTheDocument();
    });

    it("renders all next actions", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      expect(screen.getByText("Aprovar campanha")).toBeInTheDocument();
      expect(screen.getByText("Revisar métricas")).toBeInTheDocument();
      expect(screen.getByText("Ajustar targeting")).toBeInTheDocument();
    });

    it("renders insights section", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      expect(screen.getByText("Insights")).toBeInTheDocument();
    });

    it("renders all insights", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      expect(screen.getByText("Oportunidade detectada")).toBeInTheDocument();
      expect(screen.getByText("Risco identificado")).toBeInTheDocument();
      expect(screen.getByText("Dica")).toBeInTheDocument();
    });

    it("renders alerts section", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      expect(screen.getByText("Alertas")).toBeInTheDocument();
    });

    it("renders all alerts", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      expect(screen.getByText("Erro na API")).toBeInTheDocument();
      expect(screen.getByText("Performance degradada")).toBeInTheDocument();
    });
  });

  describe("next action cards", () => {
    it("shows high impact badge", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      const highImpactAction = screen.getByTestId("action-action-1");
      expect(highImpactAction).toHaveAttribute("data-impact", "high");
    });

    it("shows medium impact badge", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      const mediumImpactAction = screen.getByTestId("action-action-2");
      expect(mediumImpactAction).toHaveAttribute("data-impact", "medium");
    });

    it("shows low impact badge", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      const lowImpactAction = screen.getByTestId("action-action-3");
      expect(lowImpactAction).toHaveAttribute("data-impact", "low");
    });

    it("shows one-click indicator", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      const oneClickIndicators = screen.getAllByText("1-clique");
      expect(oneClickIndicators.length).toBeGreaterThan(0);
    });

    it("calls onExecute when action is clicked", () => {
      const onExecute = vi.fn();
      const actions = [{ ...defaultNextActions[0], onExecute }];
      render(<ActionInsightSidebar {...defaultProps} nextActions={actions} />);
      
      fireEvent.click(screen.getByText("Aprovar campanha"));
      expect(onExecute).toHaveBeenCalledTimes(1);
    });

    it("calls onActionExecute callback when action is clicked", () => {
      const onActionExecute = vi.fn();
      render(<ActionInsightSidebar {...defaultProps} onActionExecute={onActionExecute} />);
      
      fireEvent.click(screen.getByText("Aprovar campanha"));
      expect(onActionExecute).toHaveBeenCalledWith("action-1");
    });
  });

  describe("insight cards", () => {
    it("shows opportunity type with correct styling", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      const opportunityCard = screen.getByTestId("insight-insight-1");
      expect(opportunityCard).toHaveAttribute("data-type", "opportunity");
    });

    it("shows risk type with correct styling", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      const riskCard = screen.getByTestId("insight-insight-2");
      expect(riskCard).toHaveAttribute("data-type", "risk");
    });

    it("shows info type with correct styling", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      const infoCard = screen.getByTestId("insight-insight-3");
      expect(infoCard).toHaveAttribute("data-type", "info");
    });

    it("displays metrics when available", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      expect(screen.getByText("+15%")).toBeInTheDocument();
      expect(screen.getByText("85%")).toBeInTheDocument();
    });

    it("shows up trend indicator", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      const trendUp = screen.getByTestId("trend-insight-1");
      expect(trendUp).toHaveAttribute("data-trend", "up");
    });

    it("shows down trend indicator", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      const trendDown = screen.getByTestId("trend-insight-2");
      expect(trendDown).toHaveAttribute("data-trend", "down");
    });

    it("calls onInsightClick when insight is clicked", () => {
      const onInsightClick = vi.fn();
      render(<ActionInsightSidebar {...defaultProps} onInsightClick={onInsightClick} />);
      
      fireEvent.click(screen.getByText("Oportunidade detectada"));
      expect(onInsightClick).toHaveBeenCalledWith("insight-1");
    });
  });

  describe("alert cards", () => {
    it("shows critical severity with correct styling", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      const criticalAlert = screen.getByTestId("alert-alert-1");
      expect(criticalAlert).toHaveAttribute("data-severity", "critical");
    });

    it("shows warning severity with correct styling", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      const warningAlert = screen.getByTestId("alert-alert-2");
      expect(warningAlert).toHaveAttribute("data-severity", "warning");
    });

    it("shows alert timestamps", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      const timestamps = screen.getAllByTestId("alert-timestamp");
      expect(timestamps.length).toBe(2);
    });

    it("calls onAlertDismiss when dismiss button is clicked", () => {
      const onAlertDismiss = vi.fn();
      render(<ActionInsightSidebar {...defaultProps} onAlertDismiss={onAlertDismiss} />);
      
      const dismissButtons = screen.getAllByTestId("dismiss-alert");
      fireEvent.click(dismissButtons[0]);
      expect(onAlertDismiss).toHaveBeenCalledWith("alert-1");
    });
  });

  describe("empty states", () => {
    it("shows empty message when no next actions", () => {
      render(<ActionInsightSidebar {...defaultProps} nextActions={[]} />);
      expect(screen.getByText("Nenhuma ação recomendada")).toBeInTheDocument();
    });

    it("shows empty message when no insights", () => {
      render(<ActionInsightSidebar {...defaultProps} insights={[]} />);
      expect(screen.getByText("Nenhum insight disponível")).toBeInTheDocument();
    });

    it("shows empty message when no alerts", () => {
      render(<ActionInsightSidebar {...defaultProps} alerts={[]} />);
      expect(screen.getByText("Nenhum alerta ativo")).toBeInTheDocument();
    });
  });

  describe("collapsible sections", () => {
    it("toggles actions section when header is clicked", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      const actionsHeader = screen.getByTestId("actions-header");
      
      fireEvent.click(actionsHeader);
      expect(screen.queryByTestId("actions-list")).not.toBeInTheDocument();
      
      fireEvent.click(actionsHeader);
      expect(screen.getByTestId("actions-list")).toBeInTheDocument();
    });

    it("toggles insights section when header is clicked", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      const insightsHeader = screen.getByTestId("insights-header");
      
      fireEvent.click(insightsHeader);
      expect(screen.queryByTestId("insights-list")).not.toBeInTheDocument();
      
      fireEvent.click(insightsHeader);
      expect(screen.getByTestId("insights-list")).toBeInTheDocument();
    });

    it("toggles alerts section when header is clicked", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      const alertsHeader = screen.getByTestId("alerts-header");
      
      fireEvent.click(alertsHeader);
      expect(screen.queryByTestId("alerts-list")).not.toBeInTheDocument();
      
      fireEvent.click(alertsHeader);
      expect(screen.getByTestId("alerts-list")).toBeInTheDocument();
    });
  });

  describe("priority ordering", () => {
    it("orders actions by impact (high first)", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      // Find the first action card and verify it has high impact
      const firstAction = screen.getByTestId("action-action-1");
      expect(firstAction).toHaveAttribute("data-impact", "high");
    });

    it("orders alerts by severity (critical first)", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      const alerts = screen.getAllByTestId(/^alert-/);
      expect(alerts[0]).toHaveAttribute("data-severity", "critical");
    });
  });

  describe("accessibility", () => {
    it("has correct aria-label for actions section", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      const actionsHeader = screen.getByTestId("actions-header");
      expect(actionsHeader).toHaveAttribute("aria-label", "Próximas ações recomendadas");
    });

    it("has correct aria-label for insights section", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      const insightsHeader = screen.getByTestId("insights-header");
      expect(insightsHeader).toHaveAttribute("aria-label", "Insights e observações");
    });

    it("has correct aria-label for alerts section", () => {
      render(<ActionInsightSidebar {...defaultProps} />);
      const alertsHeader = screen.getByTestId("alerts-header");
      expect(alertsHeader).toHaveAttribute("aria-label", "Alertas ativos");
    });
  });
});
