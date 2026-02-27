export type DiffLineType = "unchanged" | "added" | "removed";

export type DiffLine = {
  type: DiffLineType;
  text: string;
};

export function computeLineDiff(baselineText: string, currentText: string): DiffLine[] {
  const baselineLines = baselineText.split(/\r?\n/);
  const currentLines = currentText.split(/\r?\n/);
  const output: DiffLine[] = [];

  let baselineIndex = 0;
  let currentIndex = 0;

  while (baselineIndex < baselineLines.length && currentIndex < currentLines.length) {
    const baselineLine = baselineLines[baselineIndex];
    const currentLine = currentLines[currentIndex];

    if (baselineLine === currentLine) {
      output.push({ type: "unchanged", text: baselineLine });
      baselineIndex += 1;
      currentIndex += 1;
      continue;
    }

    if (currentLines[currentIndex + 1] === baselineLine) {
      output.push({ type: "added", text: currentLine });
      currentIndex += 1;
      continue;
    }

    if (baselineLines[baselineIndex + 1] === currentLine) {
      output.push({ type: "removed", text: baselineLine });
      baselineIndex += 1;
      continue;
    }

    output.push({ type: "removed", text: baselineLine });
    output.push({ type: "added", text: currentLine });
    baselineIndex += 1;
    currentIndex += 1;
  }

  while (baselineIndex < baselineLines.length) {
    output.push({ type: "removed", text: baselineLines[baselineIndex] });
    baselineIndex += 1;
  }

  while (currentIndex < currentLines.length) {
    output.push({ type: "added", text: currentLines[currentIndex] });
    currentIndex += 1;
  }

  return output;
}
