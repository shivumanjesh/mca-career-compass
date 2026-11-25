import React from "react";

interface BarItem {
  code: string;
  label: string;
  value: number | null;
}

interface DomainBarChartProps {
  title: string;
  items: BarItem[];
  maxValue?: number;
  unit?: string;
  accentColor?: string;
}

export const DomainBarChart: React.FC<DomainBarChartProps> = ({
  title,
  items,
  maxValue = 100,
  unit = "%",
  accentColor = "#0D9488",
}) => {
  if (items.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-5 text-xs text-slate-500">
        No domain evidence recorded yet for {title}.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
      <h3 className="text-sm font-semibold text-[#0F2942]">{title}</h3>
      <div className="space-y-3" role="list" aria-label={title}>
        {items.map((item) => {
          const pct =
            item.value !== null && maxValue > 0
              ? Math.min(100, Math.max(0, (item.value / maxValue) * 100))
              : 0;
          const barColor =
            unit === "%" && item.value !== null
              ? item.value >= 70
                ? "#0D9488"
                : item.value >= 50
                  ? "#2563EB"
                  : "#E11D48"
              : accentColor;

          return (
            <div key={item.code} className="space-y-1" role="listitem">
              <div className="flex justify-between text-xs">
                <span className="font-medium text-slate-700">
                  <strong className="text-[#0F2942]">{item.code}</strong> — {item.label}
                </span>
                <span className="font-semibold text-slate-800">
                  {item.value !== null ? `${item.value}${unit}` : "Insufficient data"}
                </span>
              </div>
              <div className="h-2.5 w-full rounded-full bg-slate-100 overflow-hidden">
                {item.value !== null && (
                  <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{ width: `${pct}%`, backgroundColor: barColor }}
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

