import React from "react";

interface ScoreDistributionChartProps {
  buckets: Array<{ label: string; count: number }>;
}

export const ScoreDistributionChart: React.FC<ScoreDistributionChartProps> = ({ buckets }) => {
  const maxCount = Math.max(1, ...buckets.map((b) => b.count));

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
      <h3 className="text-sm font-semibold text-[#0F2942]">
        Demonstrated Performance Score Distribution
      </h3>
      <div className="flex items-end justify-between gap-3 h-40 pt-4 px-2 border-b border-slate-200">
        {buckets.map((bucket) => {
          const heightPct = Math.round((bucket.count / maxCount) * 100);
          return (
            <div key={bucket.label} className="flex-1 flex flex-col items-center justify-end h-full gap-1.5">
              <span className="text-xs font-semibold text-[#0F2942]">{bucket.count}</span>
              <div className="w-full max-w-[44px] bg-slate-100 rounded-t-md flex items-end h-24 overflow-hidden">
                <div
                  className="w-full bg-[#1E3A5F] rounded-t-md transition-all duration-300"
                  style={{ height: `${bucket.count > 0 ? Math.max(10, heightPct) : 0}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex justify-between gap-3 px-2 text-[11px] font-medium text-slate-600 text-center">
        {buckets.map((b) => (
          <div key={b.label} className="flex-1">{b.label}</div>
        ))}
      </div>
    </div>
  );
};

