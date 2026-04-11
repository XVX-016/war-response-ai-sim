"use client"

import { useMemo } from "react"
import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, Legend, ResponsiveContainer } from "recharts"
import { useSimStore } from "@/store/simStore"

const AXES = ["GDP", "Military", "Resources", "Population*", "Alliance", "Terrain Ease"]

function getAxisValue(nation, index, profiles) {
  const p = profiles?.[nation] ?? {}
  switch (index) {
    case 0: return Math.min(1, Math.max(0, p.gdp_index ?? 0.5))
    case 1: return Math.min(1, Math.max(0, p.military_strength ?? 0.5))
    case 2: return Math.min(1, Math.max(0, p.resource_richness ?? 0.5))
    case 3: return Math.min(1, Math.max(0, (p.population_millions ?? 5) / 20))
    case 4: return Math.min(1, Math.max(0, p.alliance_strength ?? 0.5))
    case 5: return Math.min(1, Math.max(0, 1 - (p.terrain_difficulty ?? 0.5)))
    default: return 0.5
  }
}

export default function RadarChartComponent() {
  const profiles = useSimStore((s) => s.profiles)
  const auriaName = profiles?.Auria?.pending_selection ? "Country A" : (profiles?.Auria?.display_name || "Country A")
  const borosName = profiles?.Boros?.pending_selection ? "Country B" : (profiles?.Boros?.display_name || "Country B")
  const data = useMemo(
    () =>
      AXES.map((axis, i) => ({
        axis,
        Auria: getAxisValue("Auria", i, profiles),
        Boros: getAxisValue("Boros", i, profiles),
      })),
    [profiles]
  )

  return (
    <div className="border border-[#333333] rounded p-6 bg-[#0A0A0A] h-full flex items-center">
      <ResponsiveContainer width="100%" height={360}>
        <RadarChart data={data}>
          <PolarGrid stroke="#333333" />
          <PolarAngleAxis dataKey="axis" tick={{ fill: "#A3A3A3", fontSize: 11, fontFamily: "monospace" }} />
          <PolarRadiusAxis domain={[0, 1]} tick={false} axisLine={false} />
          <Radar name={auriaName} dataKey="Auria" stroke="#3B82F6" fill="#3B82F6" fillOpacity={0.15} strokeWidth={2} dot={{ fill: "#3B82F6", r: 3 }} />
          <Radar name={borosName} dataKey="Boros" stroke="#F59E0B" fill="#F59E0B" fillOpacity={0.15} strokeWidth={2} dot={{ fill: "#F59E0B", r: 3 }} />
          <Legend wrapperStyle={{ fontFamily: "monospace", fontSize: 11, color: "#A3A3A3" }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
