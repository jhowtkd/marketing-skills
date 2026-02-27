import { describe, expect, it } from "vitest";
import { computeLineDiff } from "./diff";

describe("computeLineDiff", () => {
  it("marks added and removed lines", () => {
    const out = computeLineDiff("linha A\nlinha B", "linha A\nlinha C");
    expect(out.some((line) => line.type === "removed" && line.text.includes("linha B"))).toBe(true);
    expect(out.some((line) => line.type === "added" && line.text.includes("linha C"))).toBe(true);
  });
});
