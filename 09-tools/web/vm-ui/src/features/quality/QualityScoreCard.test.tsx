import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import QualityScoreCard from "./QualityScoreCard";

describe("QualityScoreCard", () => {
  it("renders the overall score and positive delta", () => {
    render(
      <QualityScoreCard
        current={{
          overall: 82,
          criteria: { completude: 80, estrutura: 85, clareza: 84, cta: 78, acionabilidade: 83 },
          recommendations: [],
          source: "heuristic",
        }}
        baseline={{
          overall: 60,
          criteria: { completude: 55, estrutura: 60, clareza: 63, cta: 58, acionabilidade: 64 },
          recommendations: [],
          source: "heuristic",
        }}
      />
    );

    expect(screen.getByText("Score geral")).toBeInTheDocument();
    expect(screen.getByText("82")).toBeInTheDocument();
    expect(screen.getByText("+22")).toBeInTheDocument();
  });

  it("renders a negative delta indicator", () => {
    render(
      <QualityScoreCard
        current={{
          overall: 45,
          criteria: { completude: 40, estrutura: 50, clareza: 42, cta: 44, acionabilidade: 48 },
          recommendations: [],
          source: "heuristic",
        }}
        baseline={{
          overall: 65,
          criteria: { completude: 60, estrutura: 67, clareza: 70, cta: 61, acionabilidade: 66 },
          recommendations: [],
          source: "heuristic",
        }}
      />
    );

    expect(screen.getAllByText("-20").length).toBeGreaterThan(0);
  });
});
