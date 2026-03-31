"use client"

import { useMemo } from "react"
import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, Legend, ResponsiveContainer } from "recharts"
import { useSimStore } from "@/store/simStore"

const AXES = ["GDP", "Military", "Resources", "Population*", "Alliance", "Terrain Ease"]

function getAxisValue(nation, index, profiles) {
  const p = profiles?.[nation]
  if (!p) return 0
  if (index === 0) return p.gdp_index
  if (index === 1) return p.military_strength
  if (index === 2) return p.resource_richness
  if (index === 3) return Math.min((p.population_millions || 0) / 20, 1)
  if (index === 4) return p.alliance_strength
  return 1 - p.terrain_difficulty
}

export default function RadarChartComponent() {
  const profiles = useSimStore((s) => s.profiles)
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
    <div className="border border-[#333333] rounded p-6 bg-[#0A0A0A]">
      <ResponsiveContainer width="100%" height={360}>
        <RadarChart data={data}>
          <PolarGrid stroke="#333333" />
          <PolarAngleAxis dataKey="axis" tick={{ fill: "#A3A3A3", fontSize: 11, fontFamily: "monospace" }} />
          <PolarRadiusAxis domain={[0, 1]} tick={{ fill: "#525252", fontSize: 9 }} axisLine={false} />
          <Radar name="Republic of Auria" dataKey="Auria" stroke="#3B82F6" fill="#3B82F6" fillOpacity={0.15} strokeWidth={2} dot={{ fill: "#3B82F6", r: 3 }} />
          <Radar name="Federal State of Boros" dataKey="Boros" stroke="#F59E0B" fill="#F59E0B" fillOpacity={0.15} strokeWidth={2} dot={{ fill: "#F59E0B", r: 3 }} />
          <Legend wrapperStyle={{ fontFamily: "monospace", fontSize: 11, color: "#A3A3A3" }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
