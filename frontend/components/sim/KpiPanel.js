"use client"

import { useState } from "react"
import EventLog from "@/components/sim/EventLog"

function colourForCoverage(value) {
  if (value > 0.7) return "#22C55E"
  if (value >= 0.4) return "#F59E0B"
  return "#EF4444"
}

function resourceColour(fraction) {
  if (fraction > 0.6) return "#22C55E"
  if (fraction > 0.3) return "#F59E0B"
  return "#EF4444"
}

function consequenceTone(tag) {
  const lower = String(tag || "").toLowerCase()
  if (lower.includes("risk") || lower.includes("mortality") || lower.includes("collapse")) return { bg: "#3B0000", fg: "#FCA5A5" }
  if (lower.includes("degraded") || lower.includes("impaired")) return { bg: "#3B2500", fg: "#FCD34D" }
  if (lower.includes("disrupted") || lower.includes("shortage") || lower.includes("blocked")) return { bg: "#1C1A3B", fg: "#C4B5FD" }
  return { bg: "#1A1A1A", fg: "#A3A3A3" }
}

function CountryProfileSummary({ profile }) {
  if (!profile) return null
  const rows = [
    ["GDP", profile.gdp_index, profile.gdp_index < 0.25 ? "Low" : profile.gdp_index < 0.5 ? "Medium" : profile.gdp_index < 0.75 ? "High" : "Very High"],
    ["Military", profile.military_strength, profile.military_strength < 0.25 ? "Limited" : profile.military_strength < 0.5 ? "Moderate" : profile.military_strength < 0.75 ? "Strong" : "Elite"],
    ["Resources", profile.resource_richness, profile.resource_richness < 0.35 ? "Scarce" : profile.resource_richness < 0.65 ? "Moderate" : "Rich"],
    ["Population", Math.min((profile.population_millions || 0) / 20, 1), `${Number(profile.population_millions || 0).toFixed(1)}M`],
    ["Alliance", profile.alliance_strength, profile.alliance_strength < 0.25 ? "Isolated" : profile.alliance_strength < 0.5 ? "Neutral" : profile.alliance_strength < 0.75 ? "Allied" : "Major Alliance"],
    ["Terrain Ease", 1 - profile.terrain_difficulty, profile.terrain_difficulty < 0.25 ? "Flat / Urban" : profile.terrain_difficulty < 0.5 ? "Mixed" : profile.terrain_difficulty < 0.75 ? "Mountainous" : "Extreme"],
  ]

  return (
    <details className="border border-[#333333] rounded bg-[#0A0A0A]">
      <summary className="cursor-pointer px-4 py-3 text-[11px] uppercase tracking-[0.14em] font-mono text-[#A3A3A3]">Country Profile</summary>
      <div className="px-4 pb-4">
        <div className="text-[#F5F5F5] font-semibold mb-1">{profile.display_name}</div>
        <p className="text-sm text-[#525252] italic mb-4">{profile.lore}</p>
        <div className="space-y-3">
          {rows.map(([label, value, badge]) => {
            const colour = value > 0.66 ? "#22C55E" : value > 0.33 ? "#F59E0B" : "#EF4444"
            return (
              <div key={label} className="flex items-center justify-between gap-3">
                <span className="text-xs text-[#A3A3A3] min-w-[84px]">{label}</span>
                <div className="flex-1 h-[6px] bg-[#1A1A1A] rounded overflow-hidden">
                  <div className="h-full" style={{ width: `${Math.max(0, Math.min(100, value * 100))}%`, backgroundColor: colour }} />
                </div>
                <span className="text-[10px] uppercase font-mono tracking-[0.12em] text-[#A3A3A3] min-w-[82px] text-right">{badge}</span>
              </div>
            )
          })}
        </div>
      </div>
    </details>
  )
}

function NationPanel({ nation, simState, previousState, profile, selectedAssetId, coverageMap, previousCoverageMap }) {
  const currentCoverage = coverageMap?.[nation] ?? 0
  const prevCoverage = previousCoverageMap?.[nation] ?? 0
  const displacement = (simState?.zones || []).filter((zone) => zone.nation === nation).reduce((sum, zone) => sum + (zone.displaced || 0), 0)
  const stableTurns = simState?.stable_turns_count?.[nation] ?? 0
  const endCondition = simState?.end_conditions_met?.[nation]
  const resources = simState?.resources?.[nation]?.stocks || {}
  const previousResources = previousState?.resources?.[nation]?.stocks || {}
  const consequences = simState?.active_consequences?.[nation] || []
  const selectedAsset = (simState?.assets || []).find((asset) => asset.id === selectedAssetId && asset.nation === nation)

  return (
    <div className="space-y-5">
      <div className="border border-[#333333] rounded p-4 bg-[#212020]">
        <p className="text-[11px] uppercase tracking-[0.14em] font-mono text-[#525252] mb-2">Service Coverage</p>
        <div className="text-5xl font-mono" style={{ color: colourForCoverage(currentCoverage) }}>{Math.round(currentCoverage * 100)}%</div>
        <div className="text-xs font-mono mt-1" style={{ color: currentCoverage - prevCoverage >= 0 ? "#22C55E" : "#EF4444" }}>
          {currentCoverage - prevCoverage >= 0 ? "+" : ""}{Math.round((currentCoverage - prevCoverage) * 100)} pts
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="border border-[#333333] rounded p-4 bg-[#212020]">
          <p className="text-[11px] uppercase tracking-[0.14em] font-mono text-[#525252] mb-2">Displaced Persons</p>
          <div className="text-3xl font-mono" style={{ color: displacement > 0 ? "#EF4444" : "#F5F5F5" }}>{displacement.toLocaleString()}</div>
        </div>
        <div className="border border-[#333333] rounded p-4 bg-[#212020]">
          <p className="text-[11px] uppercase tracking-[0.14em] font-mono text-[#525252] mb-2">Stable Turns</p>
          <div className="text-3xl font-mono" style={{ color: stableTurns >= 6 ? "#22C55E" : "#F5F5F5" }}>{stableTurns}</div>
        </div>
      </div>

      {endCondition ? (
        <div className="border rounded p-3 font-mono text-xs uppercase tracking-[0.15em]" style={{ borderColor: endCondition === "collapsed" ? "#EF4444" : endCondition === "stabilised" ? "#22C55E" : "#525252", color: endCondition === "collapsed" ? "#EF4444" : endCondition === "stabilised" ? "#22C55E" : "#A3A3A3" }}>
          {endCondition}
        </div>
      ) : null}

      <div className="border border-[#333333] rounded p-4 bg-[#212020]">
        <p className="text-[11px] uppercase tracking-[0.14em] font-mono text-[#525252] mb-3">Resource Stocks</p>
        <div className="space-y-3">
          {Object.entries(resources).map(([resource, amount]) => {
            const baseline = Math.max(amount, previousResources[resource] ?? amount, 1)
            const delta = amount - (previousResources[resource] ?? amount)
            const fraction = Math.max(0, Math.min(1, amount / baseline))
            return (
              <div key={resource}>
                <div className="flex items-baseline justify-between mb-1">
                  <span className="text-[10px] uppercase tracking-[0.08em] font-mono text-[#A3A3A3]">{resource.replaceAll("_", " ")}</span>
                  <span className="font-mono text-[13px] text-[#F5F5F5]">
                    {Math.round(amount)} <span className="text-[#525252] text-[11px]">u</span>{" "}
                    <span style={{ color: delta >= 0 ? "#22C55E" : "#EF4444" }}>{delta >= 0 ? "+" : ""}{Math.round(delta)}</span>
                  </span>
                </div>
                <div className="h-1 bg-[#1A1A1A] rounded overflow-hidden">
                  <div className="h-full" style={{ width: `${Math.max(0, Math.min(100, fraction * 100))}%`, backgroundColor: resourceColour(fraction) }} />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="border border-[#333333] rounded p-4 bg-[#212020]">
        <p className="text-[11px] uppercase tracking-[0.14em] font-mono text-[#525252] mb-3">Active Consequences</p>
        <div className="flex flex-wrap gap-2">
          {consequences.length === 0 ? <span className="text-sm text-[#525252]">No active consequences</span> : null}
          {consequences.map((tag) => {
            const tone = consequenceTone(tag)
            return (
              <span key={tag} className="px-2 py-1 rounded text-[10px] font-medium uppercase tracking-[0.04em]" style={{ backgroundColor: tone.bg, color: tone.fg }}>
                {tag.replaceAll("_", " ")}
              </span>
            )
          })}
        </div>
      </div>

      {selectedAsset ? (
        <div className="border border-[#333333] rounded p-4 bg-[#212020]">
          <p className="text-[11px] uppercase tracking-[0.14em] font-mono text-[#525252] mb-2">Selected Asset</p>
          <div className="text-[#F5F5F5] font-semibold">{selectedAsset.name}</div>
          <div className="text-[#A3A3A3] text-sm capitalize">{selectedAsset.asset_type.replaceAll("_", " ")}</div>
          <div className="font-mono text-sm text-[#A3A3A3] mt-1">{Math.round(selectedAsset.health)}/{Math.round(selectedAsset.max_health)} HP</div>
        </div>
      ) : null}

      {profile ? <CountryProfileSummary profile={profile} /> : null}
    </div>
  )
}

export default function KpiPanel({ simState, previousState, profiles, selectedAssetId, coverageMap, previousCoverageMap }) {
  const [tab, setTab] = useState("Auria")

  const tabs = [
    { id: "Auria", label: "Auria", accent: "#3B82F6" },
    { id: "Boros", label: "Boros", accent: "#F59E0B" },
    { id: "Events", label: "Events", accent: "#A3A3A3" },
  ]

  return (
    <div className="border border-[#333333] rounded bg-[#0A0A0A] p-4 h-full">
      <div className="flex gap-4 border-b border-[#1F1F1F] mb-4">
        {tabs.map((item) => (
          <button
            key={item.id}
            onClick={() => setTab(item.id)}
            className="pb-3 text-xs font-mono uppercase tracking-[0.14em] transition-colors"
            style={{ color: tab === item.id ? "#F5F5F5" : "#525252", borderBottom: tab === item.id ? `2px solid ${item.accent}` : "2px solid transparent" }}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === "Events" ? (
        <EventLog events={simState?.event_log || []} />
      ) : (
        <NationPanel nation={tab} simState={simState} previousState={previousState} profile={profiles?.[tab]} selectedAssetId={selectedAssetId} coverageMap={coverageMap} previousCoverageMap={previousCoverageMap} />
      )}
    </div>
  )
}
