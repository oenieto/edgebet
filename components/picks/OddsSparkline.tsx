'use client';

import { Area, AreaChart, ResponsiveContainer } from 'recharts';

interface OddsSparklineProps {
  data: number[];
  width?: number;
  height?: number;
}

/**
 * Mini sparkline showing odds movement over the last 24h.
 * `data` is an array of odds values (e.g. [1.85, 1.82, 1.80, 1.83]).
 * If no data, renders a flat placeholder line.
 */
export default function OddsSparkline({ data, width = 64, height = 24 }: OddsSparklineProps) {
  if (!data || data.length < 2) {
    return (
      <div
        className="flex items-center justify-center"
        style={{ width, height }}
      >
        <div className="w-full h-px bg-zinc-700" />
      </div>
    );
  }

  const first = data[0];
  const last = data[data.length - 1];
  const isUp = last > first;
  const color = isUp ? '#f87171' : '#34d399'; // red if odds rising (bad), green if dropping (good)

  const chartData = data.map((value, i) => ({ i, value }));

  return (
    <div style={{ width, height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 2, right: 0, left: 0, bottom: 2 }}>
          <defs>
            <linearGradient id={`spark-${isUp ? 'up' : 'down'}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#spark-${isUp ? 'up' : 'down'})`}
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
