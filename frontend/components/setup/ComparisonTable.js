"use client"

import { useSimStore } from "@/store/simStore"

const FACTORS = [
  ["GDP", (p) => p.gdp_index],
  ["Military", (p) => p.military_strength],
  ["Resources", (p) => p.resource_richness],
  ["Population", (p) => Math.min((p.population_millions || 0) / 20, 1)],
  ["Alliance", (p) => p.alliance_strength],
  ["Terrain Ease", (p) => 1 - p.terrain_difficulty],
]

export default function ComparisonTable() {
  const profiles = useSimStore((s) => s.profiles)
  const auria = profiles?.Auria
  const boros = profiles?.Boros

  if (!auria || !boros) return <div className="border border-[#333333] rounded p-6 text-[#525252]">Loading comparison…</div>

  return (
    <div className="border border-[#333333] rounded p-6 bg-[#0A0A0A] overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left border-b border-[#1F1F1F] text-[#525252] uppercase font-mono text-xs tracking-[0.15em]">
            <th className="pb-3">Factor</th>
            <th className="pb-3">Auria value</th>
            <th className="pb-3">Boros value</th>
            <th className="pb-3">Advantage</th>
          </tr>
        </thead>
        <tbody>
          {FACTORS.map(([label, getter]) => {
            const av = getter(auria)
            const bv = getter(boros)
            const equal = Math.abs(av - bv) <= 0.05
            const winner = equal ? "Equal" : av > bv ? "Auria" : "Boros"
            const winnerClass = equal ? "text-[#525252]" : winner === "Auria" ? "text-[#3B82F6]" : "text-[#F59E0B]"
            return (
              <tr key={label} className="border-b border-[#1F1F1F] text-[#A3A3A3]">
                <td className="py-3">{label}</td>
                <td className="py-3 font-mono">{Number(av).toFixed(2)}</td>
                <td className="py-3 font-mono">{Number(bv).toFixed(2)}</td>
                <td className={`py-3 font-mono ${winnerClass}`}>{winner}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
