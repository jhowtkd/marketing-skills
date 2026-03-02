import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import ImpactPreviewCard, { type ImpactPreview, type ImpactArea } from './ImpactPreviewCard';

export interface Setting {
  id: string;
  domain: string;
  label: string;
  description: string;
  value: unknown;
  type: 'boolean' | 'string' | 'number' | 'select';
  impact: 'high' | 'medium' | 'low';
  options?: string[];
}

export interface SettingChangeEvent {
  settingId: string;
  oldValue: unknown;
  newValue: unknown;
  timestamp: number;
}

interface SettingsPageProps {
  settings: Setting[];
  recommendedSettings?: string[];
  completedSettings?: string[];
  onSettingChange: (settingId: string, newValue: unknown) => void;
  onDomainExpand?: (domain: string) => void;
  onTrackTime?: (timeSpent: number) => void;
  onTrackChange?: (event: SettingChangeEvent) => void;
}

export default function SettingsPage({
  settings,
  recommendedSettings = [],
  completedSettings = [],
  onSettingChange,
  onDomainExpand,
  onTrackTime,
  onTrackChange,
}: SettingsPageProps) {
  const [expandedDomains, setExpandedDomains] = useState<Set<string>>(new Set());
  const [focusedSetting, setFocusedSetting] = useState<string | null>(null);
  const [pendingChanges, setPendingChanges] = useState<Record<string, unknown>>({});
  const mountTimeRef = useRef<number>(Date.now());

  // Track time spent on page
  useEffect(() => {
    return () => {
      if (onTrackTime) {
        const timeSpent = Date.now() - mountTimeRef.current;
        onTrackTime(timeSpent);
      }
    };
  }, [onTrackTime]);

  // Group settings by domain
  const settingsByDomain = useMemo(() => {
    const grouped: Record<string, Setting[]> = {};
    settings.forEach(setting => {
      if (!grouped[setting.domain]) {
        grouped[setting.domain] = [];
      }
      grouped[setting.domain].push(setting);
    });
    return grouped;
  }, [settings]);

  const domainOrder = useMemo(() => {
    // Sort domains by number of high-impact settings (descending)
    return Object.entries(settingsByDomain)
      .sort(([, a], [, b]) => {
        const aHighImpact = a.filter(s => s.impact === 'high').length;
        const bHighImpact = b.filter(s => s.impact === 'high').length;
        return bHighImpact - aHighImpact;
      })
      .map(([domain]) => domain);
  }, [settingsByDomain]);

  const toggleDomain = useCallback((domain: string) => {
    setExpandedDomains(prev => {
      const next = new Set(prev);
      if (next.has(domain)) {
        next.delete(domain);
      } else {
        next.add(domain);
        if (onDomainExpand) {
          onDomainExpand(domain);
        }
      }
      return next;
    });
  }, [onDomainExpand]);

  const handleSettingFocus = useCallback((settingId: string) => {
    setFocusedSetting(settingId);
  }, []);

  const handleSettingBlur = useCallback(() => {
    setFocusedSetting(null);
  }, []);

  const handleSettingChange = useCallback((setting: Setting, newValue: unknown) => {
    setPendingChanges(prev => ({ ...prev, [setting.id]: newValue }));
    
    if (onTrackChange) {
      onTrackChange({
        settingId: setting.id,
        oldValue: setting.value,
        newValue,
        timestamp: Date.now(),
      });
    }
    
    onSettingChange(setting.id, newValue);
  }, [onSettingChange, onTrackChange]);

  // Generate impact preview for focused setting
  const impactPreview: ImpactPreview | null = useMemo(() => {
    if (!focusedSetting) return null;
    
    const setting = settings.find(s => s.id === focusedSetting);
    if (!setting) return null;

    const newValue = pendingChanges[setting.id] ?? !setting.value;
    
    // Generate affected areas based on setting domain and impact
    const affectedAreas: ImpactArea[] = [];
    
    if (setting.domain === 'notifications') {
      affectedAreas.push({
        name: 'Email Delivery',
        description: 'Will affect how you receive email notifications',
        severity: setting.impact as 'high' | 'medium' | 'low',
      });
    }
    
    if (setting.domain === 'appearance') {
      affectedAreas.push({
        name: 'User Interface',
        description: 'Visual appearance will change immediately',
        severity: 'low',
      });
    }
    
    if (setting.domain === 'workflow') {
      affectedAreas.push({
        name: 'Auto-save Behavior',
        description: 'Changes how drafts are automatically saved',
        severity: setting.impact as 'high' | 'medium' | 'low',
      });
    }

    return {
      settingId: setting.id,
      settingLabel: setting.label,
      currentValue: setting.value,
      newValue,
      affectedAreas,
      requiresReload: setting.impact === 'high',
    };
  }, [focusedSetting, settings, pendingChanges]);

  // Calculate progress
  const progress = useMemo(() => {
    const total = settings.length;
    const completed = completedSettings.length;
    return total > 0 ? Math.round((completed / total) * 100) : 0;
  }, [settings.length, completedSettings.length]);

  const getDomainIcon = (domain: string) => {
    switch (domain) {
      case 'notifications':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
        );
      case 'appearance':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
          </svg>
        );
      case 'workflow':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
          </svg>
        );
      default:
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" strokeWidth={2} />
          </svg>
        );
    }
  };

  const formatDomainName = (domain: string) => {
    return domain.charAt(0).toUpperCase() + domain.slice(1);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Settings</h2>
          <p className="text-slate-600 mt-1">
            Configure your workspace preferences
          </p>
        </div>
        
        {/* Progress */}
        <div className="w-48">
          <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
            <span>Setup Progress</span>
            <span>{progress}%</span>
          </div>
          <div 
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            className="h-2 bg-slate-100 rounded-full overflow-hidden"
          >
            <div 
              className="h-full bg-[var(--vm-primary)] transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Impact Preview Card */}
      <ImpactPreviewCard
        preview={impactPreview}
        isVisible={!!focusedSetting}
      />

      {/* Domain Sections */}
      <div className="space-y-4">
        {domainOrder.map(domain => {
          const domainSettings = settingsByDomain[domain];
          const isExpanded = expandedDomains.has(domain);
          const highImpactCount = domainSettings.filter(s => s.impact === 'high').length;
          const recommendedCount = domainSettings.filter(s => recommendedSettings.includes(s.id)).length;

          return (
            <div 
              key={domain}
              className="rounded-2xl border border-slate-200 bg-white overflow-hidden"
            >
              {/* Domain Header */}
              <button
                onClick={() => toggleDomain(domain)}
                className="w-full flex items-center justify-between p-4 hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[var(--vm-warm)] flex items-center justify-center text-[var(--vm-primary)]">
                    {getDomainIcon(domain)}
                  </div>
                  <div className="text-left">
                    <h3 className="font-semibold text-slate-900">{formatDomainName(domain)}</h3>
                    <p className="text-sm text-slate-500" data-testid="domain-count">
                      {domainSettings.length} setting{domainSettings.length !== 1 ? 's' : ''}
                      {highImpactCount > 0 && (
                        <span className="ml-2 text-amber-600">• {highImpactCount} high impact</span>
                      )}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {recommendedCount > 0 && (
                    <span className="px-2 py-1 rounded-full bg-amber-100 text-amber-700 text-xs font-medium">
                      {recommendedCount} Recommended
                    </span>
                  )}
                  <svg 
                    className={`w-5 h-5 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </button>

              {/* Domain Settings */}
              {isExpanded && (
                <div className="border-t border-slate-100">
                  {domainSettings.map(setting => {
                    const isRecommended = recommendedSettings.includes(setting.id);
                    const isCompleted = completedSettings.includes(setting.id);

                    return (
                      <div
                        key={setting.id}
                        className={`
                          p-4 border-b border-slate-100 last:border-b-0
                          ${isRecommended ? 'bg-amber-50/50' : ''}
                          ${isCompleted ? 'opacity-60' : ''}
                        `}
                        onMouseEnter={() => handleSettingFocus(setting.id)}
                        onMouseLeave={handleSettingBlur}
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <label 
                                htmlFor={setting.id}
                                className="font-medium text-slate-900"
                              >
                                {setting.label}
                              </label>
                              {isRecommended && (
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-700">
                                  Recommended
                                </span>
                              )}
                              {isCompleted && (
                                <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                </svg>
                              )}
                            </div>
                            <p className="text-sm text-slate-500 mt-1">{setting.description}</p>
                            <div className="flex items-center gap-2 mt-2">
                              <span className={`
                                text-xs font-medium
                                ${setting.impact === 'high' ? 'text-red-600' : ''}
                                ${setting.impact === 'medium' ? 'text-amber-600' : ''}
                                ${setting.impact === 'low' ? 'text-slate-500' : ''}
                              `}>
                                {setting.impact} impact
                              </span>
                            </div>
                          </div>

                          {/* Toggle Switch */}
                          {setting.type === 'boolean' && (
                            <button
                              id={setting.id}
                              role="switch"
                              aria-checked={!!setting.value}
                              aria-describedby={`${setting.id}-description`}
                              onClick={() => handleSettingChange(setting, !setting.value)}
                              className={`
                                relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                                ${setting.value ? 'bg-[var(--vm-primary)]' : 'bg-slate-200'}
                              `}
                            >
                              <span
                                className={`
                                  inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                                  ${setting.value ? 'translate-x-6' : 'translate-x-1'}
                                `}
                              />
                            </button>
                          )}
                        </div>
                        <span id={`${setting.id}-description`} className="sr-only">
                          {setting.description}. Impact level: {setting.impact}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
