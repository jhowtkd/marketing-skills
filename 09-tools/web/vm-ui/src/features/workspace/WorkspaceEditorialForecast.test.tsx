import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { EditorialForecast, EditorialRecommendation } from "./useWorkspace";

// Simple component to test forecast rendering patterns
function ForecastPanel({ forecast, loading }: { forecast: EditorialForecast | null; loading: boolean }) {
  if (loading) return <div data-testid="forecast-loading">Carregando forecast...</div>;
  if (!forecast) return <div data-testid="forecast-empty">Sem dados de forecast</div>;

  const trendLabel = {
    improving: "Melhorando",
    stable: "Estável",
    degrading: "Degradando",
  }[forecast.trend];

  const riskColor = forecast.risk_score > 70 ? "text-red-600" : forecast.risk_score > 40 ? "text-yellow-600" : "text-green-600";

  return (
    <div data-testid="forecast-panel">
      <h3>Forecast Editorial</h3>
      <div data-testid="risk-score" className={riskColor}>
        Risco: {forecast.risk_score}/100
      </div>
      <div data-testid="trend">Tendência: {trendLabel}</div>
      <div data-testid="drivers">
        Drivers: {forecast.drivers.join(", ")}
      </div>
      <div data-testid="recommended-focus">
        Foco: {forecast.recommended_focus}
      </div>
    </div>
  );
}

function RecommendationWithPriority({ rec, rank }: { rec: EditorialRecommendation; rank: number }) {
  const effortBadge = rec.effort_score <= 4 ? "Baixo" : rec.effort_score <= 7 ? "Médio" : "Alto";
  const impactBadge = rec.impact_score >= 8 ? "Alto" : rec.impact_score >= 5 ? "Médio" : "Baixo";
  
  return (
    <div data-testid={`recommendation-${rank}`}>
      <div data-testid={`rank-${rank}`}>#{rank}</div>
      <div data-testid={`title-${rank}`}>{rec.title}</div>
      <div data-testid={`priority-${rank}`}>Prioridade: {rec.priority_score}</div>
      <div data-testid={`impact-${rank}`}>Impacto: {impactBadge} ({rec.impact_score}/10)</div>
      <div data-testid={`effort-${rank}`}>Esforço: {effortBadge} ({rec.effort_score}/10)</div>
      <div data-testid={`why-${rank}`}>{rec.why_priority}</div>
    </div>
  );
}

describe("Forecast Panel", () => {
  const mockForecast: EditorialForecast = {
    thread_id: "t-123",
    risk_score: 65,
    trend: "degrading",
    drivers: ["baseline_none_rate_high", "recency_gap_moderate"],
    recommended_focus: "Aumentar cobertura de golden",
    generated_at: "2026-02-27T18:00:00Z",
  };

  it("renders loading state", () => {
    render(<ForecastPanel forecast={null} loading={true} />);
    expect(screen.getByTestId("forecast-loading")).toBeInTheDocument();
  });

  it("renders empty state", () => {
    render(<ForecastPanel forecast={null} loading={false} />);
    expect(screen.getByTestId("forecast-empty")).toBeInTheDocument();
  });

  it("renders forecast with correct risk score", () => {
    render(<ForecastPanel forecast={mockForecast} loading={false} />);
    expect(screen.getByTestId("risk-score")).toHaveTextContent("Risco: 65/100");
  });

  it("renders forecast with correct trend label", () => {
    render(<ForecastPanel forecast={mockForecast} loading={false} />);
    expect(screen.getByTestId("trend")).toHaveTextContent("Tendência: Degradando");
  });

  it("renders forecast with drivers", () => {
    render(<ForecastPanel forecast={mockForecast} loading={false} />);
    expect(screen.getByTestId("drivers")).toHaveTextContent("baseline_none_rate_high");
    expect(screen.getByTestId("drivers")).toHaveTextContent("recency_gap_moderate");
  });

  it("renders forecast with recommended focus", () => {
    render(<ForecastPanel forecast={mockForecast} loading={false} />);
    expect(screen.getByTestId("recommended-focus")).toHaveTextContent("Aumentar cobertura de golden");
  });

  it("applies correct risk color for high risk", () => {
    const highRisk = { ...mockForecast, risk_score: 75 };
    render(<ForecastPanel forecast={highRisk} loading={false} />);
    expect(screen.getByTestId("risk-score")).toHaveClass("text-red-600");
  });

  it("applies correct risk color for medium risk", () => {
    render(<ForecastPanel forecast={mockForecast} loading={false} />);
    expect(screen.getByTestId("risk-score")).toHaveClass("text-yellow-600");
  });

  it("applies correct risk color for low risk", () => {
    const lowRisk = { ...mockForecast, risk_score: 30 };
    render(<ForecastPanel forecast={lowRisk} loading={false} />);
    expect(screen.getByTestId("risk-score")).toHaveClass("text-green-600");
  });
});

describe("Recommendation with Priority", () => {
  const mockRecommendation: EditorialRecommendation = {
    severity: "warning",
    reason: "baseline_none_rate_high",
    action_id: "create_objective_golden",
    title: "Criar Golden de Objetivo",
    description: "Taxa de baseline none está alta",
    impact_score: 9,
    effort_score: 4,
    priority_score: 78,
    why_priority: "Alto impacto com esforço moderado",
  };

  it("renders rank number", () => {
    render(<RecommendationWithPriority rec={mockRecommendation} rank={1} />);
    expect(screen.getByTestId("rank-1")).toHaveTextContent("#1");
  });

  it("renders title", () => {
    render(<RecommendationWithPriority rec={mockRecommendation} rank={1} />);
    expect(screen.getByTestId("title-1")).toHaveTextContent("Criar Golden de Objetivo");
  });

  it("renders priority score", () => {
    render(<RecommendationWithPriority rec={mockRecommendation} rank={1} />);
    expect(screen.getByTestId("priority-1")).toHaveTextContent("Prioridade: 78");
  });

  it("renders high impact badge", () => {
    render(<RecommendationWithPriority rec={mockRecommendation} rank={1} />);
    expect(screen.getByTestId("impact-1")).toHaveTextContent("Impacto: Alto (9/10)");
  });

  it("renders low effort badge", () => {
    render(<RecommendationWithPriority rec={mockRecommendation} rank={1} />);
    expect(screen.getByTestId("effort-1")).toHaveTextContent("Esforço: Baixo (4/10)");
  });

  it("renders why priority explanation", () => {
    render(<RecommendationWithPriority rec={mockRecommendation} rank={1} />);
    expect(screen.getByTestId("why-1")).toHaveTextContent("Alto impacto com esforço moderado");
  });

  it("renders medium impact for score 5", () => {
    const medImpact = { ...mockRecommendation, impact_score: 5 };
    render(<RecommendationWithPriority rec={medImpact} rank={2} />);
    expect(screen.getByTestId("impact-2")).toHaveTextContent("Impacto: Médio (5/10)");
  });

  it("renders high effort for score 8", () => {
    const highEffort = { ...mockRecommendation, effort_score: 8 };
    render(<RecommendationWithPriority rec={highEffort} rank={2} />);
    expect(screen.getByTestId("effort-2")).toHaveTextContent("Esforço: Alto (8/10)");
  });
});
