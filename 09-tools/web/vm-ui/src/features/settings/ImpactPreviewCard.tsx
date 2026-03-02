import { useEffect, useState } from 'react';

export interface ImpactArea {
  name: string;
  description: string;
  severity: 'high' | 'medium' | 'low';
}

export interface ImpactPreview {
  settingId: string;
  settingLabel: string;
  currentValue: unknown;
  newValue: unknown;
  affectedAreas: ImpactArea[];
  requiresReload?: boolean;
  requiresConfirmation?: boolean;
}

interface ImpactPreviewCardProps {
  preview: ImpactPreview | null;
  isVisible: boolean;
  onConfirm?: () => void;
  onCancel?: () => void;
}

export default function ImpactPreviewCard({
  preview,
  isVisible,
  onConfirm,
  onCancel,
}: ImpactPreviewCardProps) {
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    if (!isVisible) {
      setIsExiting(true);
      const timer = setTimeout(() => setIsExiting(false), 200);
      return () => clearTimeout(timer);
    }
  }, [isVisible]);

  if (!isVisible && !isExiting) return null;
  if (!preview) return null;

  const getSeverityStyles = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-red-50 border-red-200 text-red-800';
      case 'medium':
        return 'bg-amber-50 border-amber-200 text-amber-800';
      case 'low':
        return 'bg-blue-50 border-blue-200 text-blue-800';
      default:
        return 'bg-slate-50 border-slate-200 text-slate-700';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'high':
        return (
          <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        );
      case 'medium':
        return (
          <svg className="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'low':
        return (
          <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      default:
        return null;
    }
  };

  const valueToString = (value: unknown): string => {
    if (typeof value === 'boolean') return value ? 'On' : 'Off';
    if (value === null || value === undefined) return 'Not set';
    return String(value);
  };

  return (
    <div
      data-testid="impact-preview"
      className={`
        rounded-2xl border-2 border-[var(--vm-primary)] bg-white shadow-xl
        transition-all duration-200 overflow-hidden
        ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}
      `}
    >
      {/* Header */}
      <div className="bg-gradient-to-r from-[var(--vm-primary)] to-[var(--vm-primary-strong)] px-6 py-4">
        <div className="flex items-center gap-3">
          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
          <div>
            <h3 className="text-lg font-semibold text-white">Impact Preview</h3>
            <p className="text-sm text-white/80">
              Changes to <span className="font-medium">{preview.settingLabel}</span>
            </p>
          </div>
        </div>
      </div>

      {/* Value Change */}
      <div className="px-6 py-4 border-b border-slate-100">
        <p className="text-sm font-medium text-slate-500 mb-2">Value Change</p>
        <div className="flex items-center gap-3">
          <span className="px-3 py-1.5 rounded-lg bg-slate-100 text-slate-700 text-sm font-medium">
            {valueToString(preview.currentValue)}
          </span>
          <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
          <span className="px-3 py-1.5 rounded-lg bg-[var(--vm-primary)] text-white text-sm font-medium">
            {valueToString(preview.newValue)}
          </span>
        </div>
      </div>

      {/* Affected Areas */}
      <div className="px-6 py-4">
        <p className="text-sm font-medium text-slate-500 mb-3">Affects</p>
        <div className="space-y-2">
          {preview.affectedAreas.map((area, index) => (
            <div
              key={index}
              className={`
                flex items-start gap-3 p-3 rounded-xl border
                ${getSeverityStyles(area.severity)}
              `}
            >
              <div className="flex-shrink-0 mt-0.5">
                {getSeverityIcon(area.severity)}
              </div>
              <div>
                <p className="font-medium text-sm">{area.name}</p>
                <p className="text-sm opacity-80">{area.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Warnings */}
      {(preview.requiresReload || preview.requiresConfirmation) && (
        <div className="px-6 py-3 bg-amber-50 border-t border-amber-100">
          {preview.requiresReload && (
            <div className="flex items-center gap-2 text-amber-700 text-sm">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>Page reload required for changes to take effect</span>
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      {(onConfirm || onCancel) && (
        <div className="px-6 py-4 border-t border-slate-100 flex gap-3 justify-end">
          {onCancel && (
            <button
              onClick={onCancel}
              className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 text-sm font-medium hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
          )}
          {onConfirm && (
            <button
              onClick={onConfirm}
              className="px-4 py-2 rounded-xl bg-[var(--vm-primary)] text-white text-sm font-medium hover:opacity-90 transition-opacity"
            >
              Apply Change
            </button>
          )}
        </div>
      )}
    </div>
  );
}
