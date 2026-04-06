"use client"

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded border border-[#333333] bg-[#212020] px-3 py-2 text-xs font-mono">
      <p className="mb-1 text-[#525252]">Turn {label}</p>
      {payload.map((item) => (
        <p key={item.name} style={{ color: item.color }}>
          {item.name}: {(item.value * 100).toFixed(1)}%
        </p>
      ))}
    </div>
  )
}

export default function Timeline({ history = [] }) {
  if (history.length < 2) {
    return (
      <div className="flex h-[160px] items-center justify-center rounded border border-[#1F1F1F]">
        <p className="text-xs font-mono text-[#525252]">Advance 2+ turns to see coverage timeline</p>
      </div>
    )
  }

  const data = history.map((entry) => ({
    turn: entry.turn,
    Auria: entry.service_coverage?.Auria ?? 0,
    Boros: entry.service_coverage?.Boros ?? 0,
  }))

  return (
    <div className="rounded border border-[#1F1F1F] p-3">
      <p className="mb-3 text-[10px] font-mono uppercase tracking-[0.15em] text-[#525252]">Service Coverage Timeline</p>
      <ResponsiveContainer width="100%" height={140}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid stroke="#1F1F1F" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="turn"
            tick={{ fill: "#525252", fontSize: 9, fontFamily: "monospace" }}
            axisLine={{ stroke: "#333333" }}
            tickLine={false}
          />
          <YAxis
            domain={[0, 1]}
            tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
            tick={{ fill: "#525252", fontSize: 9, fontFamily: "monospace" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            y={0.7}
            stroke="#22C55E"
            strokeDasharray="4 4"
            strokeOpacity={0.4}
            label={{ value: "70%", fill: "#22C55E", fontSize: 9, fontFamily: "monospace" }}
          />
          <ReferenceLine
            y={0.5}
            stroke="#EF4444"
            strokeDasharray="4 4"
            strokeOpacity={0.4}
            label={{ value: "50%", fill: "#EF4444", fontSize: 9, fontFamily: "monospace" }}
          />
          <Line
            type="monotone"
            dataKey="Auria"
            stroke="#3B82F6"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 3, fill: "#3B82F6" }}
            isAnimationActive
            animationDuration={300}
          />
          <Line
            type="monotone"
            dataKey="Boros"
            stroke="#F59E0B"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 3, fill: "#F59E0B" }}
            isAnimationActive
            animationDuration={300}
          />
          <Legend
            wrapperStyle={{
              fontFamily: "monospace",
              fontSize: 10,
              color: "#A3A3A3",
              paddingTop: "8px",
            }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
