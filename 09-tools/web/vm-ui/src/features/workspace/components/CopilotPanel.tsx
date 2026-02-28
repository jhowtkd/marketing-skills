import { useState } from "react";

type Suggestion = {
  suggestion_id: string;
  content: string;
  confidence: number;
  reason_codes: string[];
  why: string;
  expected_impact: { quality_delta: number; approval_lift: number };
  created_at: string;
};

type FeedbackAction = "accepted" | "edited" | "ignored";

// v14: Segment Status Type
type SegmentStatus = {
  segment_key: string;
  segment_status: "eligible" | "insufficient_volume" | "frozen" | "fallback";
  is_eligible: boolean;
  segment_runs_total: number;
  adjustment_factor: number;
  explanation?: string;
};

type CopilotPanelProps = {
  suggestions: Suggestion[];
  phase: "initial" | "refine" | "strategy";
  guardrailApplied: boolean;
  loading: boolean;
  onRefresh: (phase: "initial" | "refine" | "strategy") => void;
  onFeedback: (payload: {
    suggestion_id: string;
    action: FeedbackAction;
    edited_content?: string;
  }) => void;
  // v14: Optional segment status for personalization badges
  segmentStatus?: SegmentStatus | null;
};

const phaseLabels: Record<string, string> = {
  initial: "Inicial",
  refine: "Refinar",
  strategy: "Estratégia",
};

const reasonCodeLabels: Record<string, string> = {
  high_success_rate: "Alta taxa de sucesso",
  success_rate: "Taxa de sucesso",
  high_quality: "Alta qualidade",
  quality: "Qualidade",
  fast: "Rápido",
  low_sample_size: "Amostra pequena",
  fallback_default: "Padrão",
  scorecard_gaps: "Lacunas no scorecard",
  high_risk_detected: "Risco alto detectado",
  risk_detected: "Risco detectado",
  no_gaps_identified: "Sem lacunas",
  no_risk_signals: "Sem sinais de risco",
};

function humanizeReasonCode(code: string): string {
  return reasonCodeLabels[code] || code;
}

function getConfidenceClasses(confidence: number): string {
  if (confidence >= 0.7) return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100";
  if (confidence >= 0.4) return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100";
  return "bg-gray-100 text-gray-800";
}

// v14: Segment status badge helpers
function getSegmentBadgeClasses(status: SegmentStatus["segment_status"]): string {
  if (status === "eligible") {
    return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100";
  }
  return "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400";
}

function getSegmentBadgeLabel(status: SegmentStatus["segment_status"]): string {
  if (status === "eligible") {
    return "Personalização ativa";
  }
  return "Fallback global";
}

function formatSegmentRuns(status: SegmentStatus): string {
  if (status.segment_status === "eligible") {
    return `${status.segment_runs_total} runs`;
  }
  return `${status.segment_runs_total}/20 runs`;
}

function formatAdjustmentFactor(factor: number): string {
  const percent = Math.round(factor * 100);
  if (percent > 0) return `+${percent}%`;
  if (percent < 0) return `${percent}%`;
  return "0%";
}

export function CopilotPanel({
  suggestions,
  phase,
  guardrailApplied,
  loading,
  onRefresh,
  onFeedback,
  segmentStatus,
}: CopilotPanelProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editedContent, setEditedContent] = useState("");

  const handleEdit = (suggestion: Suggestion) => {
    setEditingId(suggestion.suggestion_id);
    setEditedContent(suggestion.content);
  };

  const handleApplyEdit = (suggestionId: string) => {
    onFeedback({
      suggestion_id: suggestionId,
      action: "edited",
      edited_content: editedContent,
    });
    setEditingId(null);
    setEditedContent("");
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditedContent("");
  };

  if (loading) {
    return (
      <div className="rounded-lg border p-4" data-testid="copilot-panel">
        <h3 className="text-lg font-semibold mb-3">Copilot Editorial</h3>
        <div className="flex items-center gap-2 text-gray-500">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          Carregando sugestões...
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border p-4" data-testid="copilot-panel">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold">Copilot Editorial</h3>
        
        {/* v14: Segment Status Badge */}
        {segmentStatus && (
          <div className="flex items-center gap-2">
            <span
              className={`px-2 py-1 text-xs font-medium rounded-full ${getSegmentBadgeClasses(segmentStatus.segment_status)}`}
              title={segmentStatus.explanation || getSegmentBadgeLabel(segmentStatus.segment_status)}
              data-testid="segment-badge"
            >
              {getSegmentBadgeLabel(segmentStatus.segment_status)}
            </span>
            <span className="text-xs text-gray-500">
              {formatSegmentRuns(segmentStatus)}
            </span>
          </div>
        )}
      </div>

      <div className="flex gap-1 mb-4">
        {(["initial", "refine", "strategy"] as const).map((p) => (
          <button
            key={p}
            onClick={() => onRefresh(p)}
            className={`px-3 py-1 text-sm rounded-md transition-colors ${
              phase === p
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            {phaseLabels[p]}
          </button>
        ))}
      </div>

      {guardrailApplied && suggestions.length === 0 && (
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 dark:border-yellow-900 dark:bg-yellow-950 mb-4">
          <p className="text-sm text-yellow-800 dark:text-yellow-200">
            Confiança insuficiente para gerar sugestões ativas.
            Continue com as configurações atuais ou forneça mais contexto.
          </p>
        </div>
      )}

      {suggestions.length === 0 && !guardrailApplied && (
        <p className="text-sm text-gray-500">
          Nenhuma sugestão disponível para esta fase.
        </p>
      )}

      {/* v14: Dev Info (only when segment status is provided) */}
      {segmentStatus && (
        <div className="mb-4 p-2 bg-gray-50 dark:bg-gray-900 rounded text-xs font-mono text-gray-600 dark:text-gray-400">
          <div className="flex items-center gap-2">
            <span>segment:</span>
            <span className="text-blue-600 dark:text-blue-400">{segmentStatus.segment_key}</span>
            <span>|</span>
            <span className={segmentStatus.is_eligible ? "text-green-600" : "text-gray-500"}>
              {segmentStatus.segment_status}
            </span>
            <span>|</span>
            <span>adj: {formatAdjustmentFactor(segmentStatus.adjustment_factor)}</span>
          </div>
        </div>
      )}

      {suggestions.map((suggestion) => (
        <div
          key={suggestion.suggestion_id}
          className="rounded-lg border p-4 space-y-3 mb-3"
        >
          {/* Header: Confidence and Impact */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${getConfidenceClasses(suggestion.confidence)}`}>
                {Math.round(suggestion.confidence * 100)}% confiança
              </span>
              {suggestion.expected_impact.quality_delta > 0 && (
                <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                  +{suggestion.expected_impact.quality_delta} pts
                </span>
              )}
            </div>
          </div>

          {/* Content */}
          {editingId === suggestion.suggestion_id ? (
            <div className="space-y-2">
              <textarea
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
                placeholder="Edite a sugestão..."
                className="w-full min-h-[100px] p-2 border rounded-md text-sm"
              />
              <div className="flex gap-2">
                <button
                  className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
                  onClick={() => handleApplyEdit(suggestion.suggestion_id)}
                >
                  Aplicar Edição
                </button>
                <button
                  className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                  onClick={handleCancelEdit}
                >
                  Cancelar
                </button>
              </div>
            </div>
          ) : (
            <>
              <p className="text-sm whitespace-pre-wrap">{suggestion.content}</p>

              {/* Why */}
              {suggestion.why && (
                <p className="text-xs text-gray-500">{suggestion.why}</p>
              )}

              {/* Reason Codes */}
              {suggestion.reason_codes.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {suggestion.reason_codes.map((code) => (
                    <span
                      key={code}
                      className="px-2 py-0.5 text-xs border rounded-full text-gray-600"
                    >
                      {humanizeReasonCode(code)}
                    </span>
                  ))}
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2 pt-2">
                <button
                  className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
                  onClick={() =>
                    onFeedback({
                      suggestion_id: suggestion.suggestion_id,
                      action: "accepted",
                    })
                  }
                >
                  Aplicar
                </button>
                <button
                  className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                  onClick={() => handleEdit(suggestion)}
                >
                  Editar
                </button>
                <button
                  className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
                  onClick={() =>
                    onFeedback({
                      suggestion_id: suggestion.suggestion_id,
                      action: "ignored",
                    })
                  }
                >
                  Ignorar
                </button>
              </div>
            </>
          )}
        </div>
      ))}
    </div>
  );
}
