import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import VersionDiffPanel from "./VersionDiffPanel";

describe("VersionDiffPanel", () => {
  it("renders added and removed blocks", () => {
    render(<VersionDiffPanel baselineText={"linha A\nlinha B"} currentText={"linha A\nlinha C"} />);

    expect(screen.getByText("Blocos adicionados")).toBeInTheDocument();
    expect(screen.getByText("Blocos removidos")).toBeInTheDocument();
    expect(screen.getByText("linha B")).toBeInTheDocument();
    expect(screen.getByText("linha C")).toBeInTheDocument();
  });
});
