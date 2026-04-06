"use client"

import { useSimStore } from "@/store/simStore"

const CITY_REFS = [
  { pop: 10000, name: "a small town" },
  { pop: 100000, name: "a mid-sized city" },
  { pop: 500000, name: "a city the size of Lyon" },
  { pop: 1000000, name: "a city the size of Vienna" },
  { pop: 3000000, name: "a city the size of Berlin" },
  { pop: 9000000, name: "a city the size of London" },
  { pop: 20000000, name: "a megacity" },
]

function populationAnchor(n) {
  if (n === 0) return null
  const ref = [...CITY_REFS].reverse().find((entry) => n >= entry.pop) ?? CITY_REFS[0]
  return ref.name
}

function computeCriticalPath(simState, nation) {
  if (!simState) return null
  const weights = {
    power_plant: 0.25,
    water_treatment: 0.2,
    hospital: 0.2,
    telecom_tower: 0.05,
    transport_hub: 0.1,
    fuel_depot: 0.05,
    shelter: 0.05,
    command_center: 0.1,
  }
  const assets = (simState.assets || []).filter((asset) => asset.nation === nation && !asset.is_destroyed && asset.health < asset.max_health)
  if (!assets.length) return null

  let bestAsset = null
  let bestGain = 0
  for (const asset of assets) {
    const currentFrac = asset.health / asset.max_health
    const repairedFrac = Math.min(1, (asset.health + 30) / asset.max_health)
    const gain = (weights[asset.asset_type] || 0) * (repairedFrac - currentFrac)
    if (gain > bestGain) {
      bestGain = gain
      bestAsset = asset
    }
  }
  return bestAsset ? { asset: bestAsset, coverageGain: bestGain } : null
}

export default function InsightsPanel() {
  const simState = useSimStore((s) => s.simState)
  const history = useSimStore((s) => s.history)

  if (!simState || simState.turn === 0) return null

  const nations = simState.nations || []

  return (
    <div style={{ border: "1px solid #333333", borderRadius: "4px", background: "#212020", padding: "16px", marginBottom: "12px" }}>
      <div style={{ fontFamily: "Space Mono, monospace", fontSize: "9px", letterSpacing: "0.15em", textTransform: "uppercase", color: "#525252", marginBottom: "12px" }}>
        Situation Analysis
      </div>

      <div style={{ display: "grid", gridTemplateColumns: nations.length > 1 ? "1fr 1fr" : "1fr", gap: "16px" }}>
        {nations.map((nation, index) => {
          const coverage = simState.service_coverage_score?.(nation) ?? 0
          const zones = (simState.zones || []).filter((zone) => zone.nation === nation)
          const totalDisp = zones.reduce((sum, zone) => sum + (zone.displaced || 0), 0)
          const totalPop = zones.reduce((sum, zone) => sum + (zone.population || 0), 0)
          const critPath = computeCriticalPath(simState, nation)
          const anchor = populationAnchor(totalDisp)
          const nationCol = index === 0 ? "#3B82F6" : "#F59E0B"
          const prevCoverage = history.length >= 2 ? history[history.length - 2]?.service_coverage?.[nation] ?? coverage : coverage
          const trend = coverage - prevCoverage

          return (
            <div key={nation}>
              <div style={{ fontFamily: "Space Mono, monospace", fontSize: "10px", letterSpacing: "0.1em", textTransform: "uppercase", color: nationCol, marginBottom: "10px" }}>
                {nation}
              </div>

              <div style={{ fontFamily: "Space Mono, monospace", fontSize: "24px", fontWeight: 400, color: coverage > 0.7 ? "#22C55E" : coverage > 0.4 ? "#F59E0B" : "#EF4444", letterSpacing: "-0.02em", marginBottom: "2px" }}>
                {(coverage * 100).toFixed(1)}%
                <span style={{ fontSize: "11px", fontWeight: 400, color: trend >= 0 ? "#22C55E" : "#EF4444", marginLeft: "8px" }}>
                  {trend >= 0 ? "▲" : "▼"} {Math.abs(trend * 100).toFixed(1)}%
                </span>
              </div>
              <div style={{ fontFamily: "Space Grotesk, sans-serif", fontSize: "11px", color: "#525252", marginBottom: "12px" }}>
                Service coverage
              </div>

              {totalDisp > 0 ? (
                <div style={{ background: "#3B000033", border: "1px solid #EF444433", borderRadius: "3px", padding: "8px 10px", marginBottom: "10px" }}>
                  <div style={{ fontFamily: "Space Mono, monospace", fontSize: "13px", color: "#EF4444", letterSpacing: "-0.01em" }}>
                    {totalDisp.toLocaleString()} displaced
                  </div>
                  {anchor ? (
                    <div style={{ fontFamily: "Space Grotesk, sans-serif", fontSize: "11px", color: "#A3A3A3", marginTop: "2px" }}>
                      Equivalent to the population of {anchor}
                    </div>
                  ) : null}
                  <div style={{ fontFamily: "Space Mono, monospace", fontSize: "10px", color: "#525252", marginTop: "4px" }}>
                    {totalPop > 0 ? ((totalDisp / totalPop) * 100).toFixed(1) : "0.0"}% of population
                  </div>
                </div>
              ) : null}

              {critPath ? (
                <div style={{ background: "#1A1A2E", border: "1px solid #3B82F633", borderRadius: "3px", padding: "8px 10px" }}>
                  <div style={{ fontFamily: "Space Mono, monospace", fontSize: "9px", letterSpacing: "0.1em", textTransform: "uppercase", color: "#3B82F6", marginBottom: "4px" }}>
                    Recommended action
                  </div>
                  <div style={{ fontFamily: "Space Grotesk, sans-serif", fontSize: "12px", color: "#F5F5F5", marginBottom: "2px" }}>
                    Repair {critPath.asset.name}
                  </div>
                  <div style={{ fontFamily: "Space Mono, monospace", fontSize: "10px", color: "#3B82F6" }}>
                    +{(critPath.coverageGain * 100).toFixed(1)}% coverage gain
                  </div>
                  <div style={{ fontFamily: "Space Grotesk, sans-serif", fontSize: "11px", color: "#525252", marginTop: "2px" }}>
                    Current: {critPath.asset.health.toFixed(0)}/{critPath.asset.max_health} HP
                  </div>
                </div>
              ) : null}
            </div>
          )
        })}
      </div>
    </div>
  )
}
