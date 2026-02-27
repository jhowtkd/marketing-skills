export type GuidedPreset = "mais_profundo" | "mais_persuasivo" | "mais_claro";

export const GUIDED_PRESET_DEFINITIONS: Record<GuidedPreset, { label: string; instruction: string }> = {
  mais_profundo: {
    label: "Mais profundo",
    instruction: "Aprofunde analise, contexto e justificativas praticas.",
  },
  mais_persuasivo: {
    label: "Mais persuasivo",
    instruction: "Reforce argumentos de valor e orientacao para conversao.",
  },
  mais_claro: {
    label: "Mais claro",
    instruction: "Simplifique linguagem e organize a leitura por blocos.",
  },
};

export type BuildGuidedRequestInput = {
  baseRequest: string;
  presets: string[];
  userGuidance: string;
  weakPoints: string[];
};

export function buildGuidedRequest(input: BuildGuidedRequestInput): string {
  const baseRequest = input.baseRequest.trim();
  const weakPoints = input.weakPoints.map((point) => point.trim()).filter(Boolean);
  const presets = input.presets
    .map((preset) => GUIDED_PRESET_DEFINITIONS[preset as GuidedPreset]?.instruction ?? preset)
    .filter(Boolean);
  const guidance = input.userGuidance.trim();

  const sections = [`Pedido base: ${baseRequest}`];

  if (weakPoints.length > 0) {
    sections.push(`Pontos fracos a corrigir: ${weakPoints.join("; ")}`);
  }

  if (presets.length > 0) {
    sections.push(`Ajustes guiados: ${presets.join("; ")}`);
  }

  if (guidance) {
    sections.push(`Guia adicional: ${guidance}`);
  }

  return sections.join("\n\n").trim();
}
