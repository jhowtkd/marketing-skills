interface SliderProps {
  label: string;
  leftLabel?: string;
  rightLabel?: string;
  value: number;
  min?: number;
  max?: number;
  onChange: (value: number) => void;
}

export function Slider({
  label,
  leftLabel,
  rightLabel,
  value,
  min = 0,
  max = 100,
  onChange,
}: SliderProps) {
  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-gray-700">{label}</label>
      <div className="flex items-center gap-3">
        {leftLabel && <span className="text-xs text-gray-500 w-16 text-right">{leftLabel}</span>}
        <input
          type="range"
          min={min}
          max={max}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
        />
        {rightLabel && <span className="text-xs text-gray-500 w-16">{rightLabel}</span>}
      </div>
    </div>
  );
}
