import { describe, expect, it } from "vitest";
import { buildMarkdownFilename } from "./ArtifactPreview";

describe("buildMarkdownFilename", () => {
  it("generates markdown filename", () => {
    expect(buildMarkdownFilename("Versao 3")).toBe("versao-3.md");
  });
});
