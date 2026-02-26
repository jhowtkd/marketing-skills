import { describe, expect, it } from "vitest";
import { readWorkspaceView, writeWorkspaceView } from "./viewState";

describe("workspace view state", () => {
  it("defaults to studio when no value exists", () => {
    expect(readWorkspaceView(`job-default-${Date.now()}`)).toBe("studio");
  });

  it("persists and reads chat view per job", () => {
    const jobOne = `job-1-${Date.now()}`;
    const jobTwo = `job-2-${Date.now()}`;
    writeWorkspaceView(jobOne, "chat");
    expect(readWorkspaceView(jobOne)).toBe("chat");
    expect(readWorkspaceView(jobTwo)).toBe("studio");
  });
});
