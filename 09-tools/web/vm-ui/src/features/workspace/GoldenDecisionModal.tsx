import { useState } from "react";

type Props = {
  isOpen: boolean;
  scope: "global" | "objective";
  onClose: () => void;
  onSubmit: (input: { justification: string }) => void;
};

export function GoldenDecisionModal({ isOpen, scope, onClose, onSubmit }: Props) {
  const [justification, setJustification] = useState("");

  if (!isOpen) return null;

  const title = scope === "global" ? "Definir como golden global" : "Definir como golden deste objetivo";
  const description =
    scope === "global"
      ? "Esta versao sera marcada como a melhor referencia global para todas as comparacoes neste job."
      : "Esta versao sera marcada como a melhor referencia para este objetivo especifico.";

  const canSubmit = justification.trim().length > 0;

  const handleSubmit = () => {
    if (!canSubmit) return;
    onSubmit({ justification: justification.trim() });
    setJustification("");
  };

  const handleClose = () => {
    setJustification("");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        <p className="mt-2 text-sm text-slate-600">{description}</p>

        <div className="mt-4">
          <label htmlFor="justification" className="block text-sm font-medium text-slate-700">
            Justificativa <span className="text-red-500">*</span>
          </label>
          <textarea
            id="justification"
            rows={3}
            value={justification}
            onChange={(e) => setJustification(e.target.value)}
            placeholder="Explique por que esta versao deve ser considerada a melhor referencia..."
            className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-[var(--vm-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--vm-primary)]"
          />
          <p className="mt-1 text-xs text-slate-500">
            A justificativa e obrigatoria e ajuda a rastrear decisoes editoriais.
          </p>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={handleClose}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-900 hover:bg-slate-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            disabled={!canSubmit}
            onClick={handleSubmit}
            className="rounded-xl bg-[var(--vm-primary)] px-4 py-2 text-sm font-medium text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--vm-primary-strong)]"
          >
            Confirmar
          </button>
        </div>
      </div>
    </div>
  );
}

export default GoldenDecisionModal;
