import { useMemo, useState } from "react";
import { buildGuidedRequest, GUIDED_PRESET_DEFINITIONS, type GuidedPreset } from "./guidedRegenerate";

export type GuidedRegenerateSubmitPayload = {
  presets: GuidedPreset[];
  userGuidance: string;
  requestText: string;
};

type Props = {
  isOpen: boolean;
  baseRequest: string;
  weakPoints: string[];
  onClose: () => void;
  onSubmit: (payload: GuidedRegenerateSubmitPayload) => void;
};

export default function GuidedRegenerateModal({ isOpen, baseRequest, weakPoints, onClose, onSubmit }: Props) {
  const [selectedPresets, setSelectedPresets] = useState<GuidedPreset[]>([]);
  const [userGuidance, setUserGuidance] = useState("");

  const presetEntries = useMemo(
    () => Object.entries(GUIDED_PRESET_DEFINITIONS) as Array<[GuidedPreset, (typeof GUIDED_PRESET_DEFINITIONS)[GuidedPreset]]>,
    []
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" role="dialog" aria-modal>
      <div className="w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-5 shadow-xl">
        <h3 className="text-base font-semibold text-slate-900">Regeneracao guiada</h3>
        <p className="mt-1 text-sm text-slate-600">Escolha ajustes e descreva orientacoes extras para a nova versao.</p>

        <fieldset className="mt-4 space-y-2">
          <legend className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Presets</legend>
          {presetEntries.map(([id, preset]) => (
            <label key={id} className="flex items-start gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={selectedPresets.includes(id)}
                onChange={(event) => {
                  if (event.target.checked) {
                    setSelectedPresets((current) => [...current, id]);
                  } else {
                    setSelectedPresets((current) => current.filter((value) => value !== id));
                  }
                }}
              />
              <span>{preset.label}</span>
            </label>
          ))}
        </fieldset>

        <label className="mt-4 block text-xs font-semibold uppercase tracking-[0.14em] text-slate-500" htmlFor="guided-extra">
          Guia adicional
        </label>
        <textarea
          id="guided-extra"
          aria-label="Guia adicional"
          value={userGuidance}
          onChange={(event) => setUserGuidance(event.target.value)}
          rows={4}
          className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900"
        />

        <div className="mt-4 flex items-center justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
            Fechar
          </button>
          <button
            type="button"
            className="rounded-xl bg-primary px-3 py-2 text-sm font-medium text-white"
            onClick={() => {
              const requestText = buildGuidedRequest({
                baseRequest,
                presets: selectedPresets,
                userGuidance,
                weakPoints,
              });
              onSubmit({ presets: selectedPresets, userGuidance, requestText });
            }}
          >
            Gerar versao guiada
          </button>
        </div>
      </div>
    </div>
  );
}
