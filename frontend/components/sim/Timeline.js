"use client"

import { useMemo } from "react"
import { Line, LineChart, CartesianGrid, ResponsiveContainer, ReferenceLine, Tooltip, XAxis, YAxis } from "recharts"

export default function Timeline({ history }) {
  const data = useMemo(() => {
    return (history || []).map((entry) => ({
      turn: entry.turn,
      Auria: Math.round(((entry.service_coverage?.Auria ?? 0) * 100) * 10) / 10,
      Boros: Math.round(((entry.service_coverage?.Boros ?? 0) * 100) * 10) / 10,
    }))
  }, [history])

  if (!data || data.length < 2) return null

  return (
    <div className="border border-[#333333] rounded bg-[#212020] p-4 h-[210px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid stroke="#333333" strokeDasharray="3 3" />
          <XAxis dataKey="turn" tick={{ fill: "#525252", fontSize: 11, fontFamily: "monospace" }} tickLine={false} axisLine={{ stroke: "#333333" }} />
          <YAxis domain={[0, 100]} tick={{ fill: "#525252", fontSize: 11, fontFamily: "monospace" }} tickLine={false} axisLine={{ stroke: "#333333" }} />
          <Tooltip contentStyle={{ background: "#212020", border: "1px solid #333333", color: "#F5F5F5" }} labelStyle={{ color: "#A3A3A3" }} />
          <ReferenceLine y={50} stroke="#EF4444" strokeDasharray="4 4" />
          <ReferenceLine y={70} stroke="#22C55E" strokeDasharray="4 4" />
          <Line type="monotone" dataKey="Auria" stroke="#3B82F6" strokeWidth={2} dot={false} isAnimationActive />
          <Line type="monotone" dataKey="Boros" stroke="#F59E0B" strokeWidth={2} dot={false} isAnimationActive />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
