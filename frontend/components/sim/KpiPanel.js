"use client"

import { useState } from "react"
import EventLog from "@/components/sim/EventLog"
import { useNationDisplayNames } from "@/lib/nations"

function colourForCoverage(value) {
  if (value > 0.7) return "#22C55E"
  if (value >= 0.4) return "#F59E0B"
  return "#EF4444"
}

function displacedColour(value) {
  return value > 0 ? "#EF4444" : "#525252"
}

function stableTurnsColour(value) {
  if (value >= 8) return "#22C55E"
  if (value === 7) return "#A3A3A3"
  if (value >= 4) return "#F59E0B"
  return "#525252"
}

function resourceColour(fraction) {
  if (fraction > 0.6) return "#22C55E"
  if (fraction > 0.3) return "#F59E0B"
  return "#EF4444"
}

function consequenceTone(tag) {
  const lower = String(tag || "").toLowerCase()
  if (lower.includes("risk") || lower.includes("mortality") || lower.includes("collapse")) return { bg: "#3B0000", fg: "#FCA5A5" }
  if (lower.includes("degraded") || lower.includes("impaired") || lower.includes("reduced")) return { bg: "#3B2500", fg: "#FCD34D" }
  if (lower.includes("disrupted") || lower.includes("blocked") || lower.includes("shortage")) return { bg: "#1C1A3B", fg: "#C4B5FD" }
  return { bg: "#1A1A1A", fg: "#A3A3A3" }
}

function EndConditionBanner({ condition }) {
  if (!condition) return null

  const config = {
    stabilised: { label: "STABILISED", bg: "#14291A", border: "#22C55E", text: "#86EFAC", icon: "✓" },
    collapsed: { label: "COLLAPSED", bg: "#3B0000", border: "#EF4444", text: "#FCA5A5", icon: "✕" },
    timeout: { label: "TIMEOUT", bg: "#1A1A1A", border: "#525252", text: "#A3A3A3", icon: "—" },
  }[condition] ?? null

  if (!config) return null

  return (
    <div className="mb-4 flex items-center gap-3 rounded border px-4 py-3 font-mono" style={{ background: config.bg, borderColor: config.border }}>
      <span className="text-lg" style={{ color: config.border }}>{config.icon}</span>
      <div>
        <p className="text-[11px] font-semibold tracking-[0.15em]" style={{ color: config.text }}>{config.label}</p>
        <p className="mt-0.5 text-[10px] text-[#525252]">
          {condition === "stabilised" && "All critical assets stable for 8 consecutive turns"}
          {condition === "collapsed" && "National service coverage fell below 20%"}
          {condition === "timeout" && "Simulation reached turn limit"}
        </p>
      </div>
    </div>
  )
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
    <details className="rounded border border-[#333333] bg-[#0A0A0A]">
      <summary className="cursor-pointer px-4 py-3 text-[11px] font-mono uppercase tracking-[0.14em] text-[#A3A3A3]">Country Profile</summary>
      <div className="px-4 pb-4">
        <div className="mb-1 font-semibold text-[#F5F5F5]">{profile.display_name}</div>
        <p className="mb-4 text-sm italic text-[#525252]">{profile.lore}</p>
        <div className="space-y-3">
          {rows.map(([label, value, badge]) => {
            const colour = value > 0.66 ? "#22C55E" : value > 0.33 ? "#F59E0B" : "#EF4444"
            return (
              <div key={label} className="flex items-center justify-between gap-3">
                <span className="min-w-[84px] text-xs text-[#A3A3A3]">{label}</span>
                <div className="h-[6px] flex-1 overflow-hidden rounded bg-[#1A1A1A]">
                  <div className="h-full" style={{ width: `${Math.max(0, Math.min(100, value * 100))}%`, backgroundColor: colour }} />
                </div>
                <span className="min-w-[82px] text-right text-[10px] font-mono uppercase tracking-[0.12em] text-[#A3A3A3]">{badge}</span>
              </div>
            )
          })}
        </div>
      </div>
    </details>
  )
}

function AssetDetail({ asset }) {
  if (!asset) return null

  const STATUS_COLOUR = {
    healthy: "#22C55E",
    degraded: "#F59E0B",
    critical: "#EF4444",
    destroyed: "#525252",
  }

  const healthFraction = asset.max_health > 0 ? asset.health / asset.max_health : 0
  const status = asset.is_destroyed ? "destroyed" : healthFraction >= 0.8 ? "healthy" : healthFraction >= 0.5 ? "degraded" : "critical"
  const barColour = STATUS_COLOUR[status]

  return (
    <div className="mt-4 rounded border border-[#333333] p-4">
      <div className="mb-3 flex items-start justify-between">
        <div>
          <p className="mb-1 text-[10px] font-mono uppercase tracking-[0.15em] text-[#525252]">{asset.asset_type?.replace(/_/g, " ")}</p>
          <h3 className="text-sm font-semibold text-[#F5F5F5]">{asset.name}</h3>
          <p className="mt-0.5 text-[11px] font-mono text-[#525252]">{asset.nation} · Row {asset.row}, Col {asset.col}</p>
        </div>
        <span className="rounded-sm border px-2 py-1 text-[10px] font-mono uppercase tracking-wider" style={{ color: barColour, borderColor: `${barColour}44`, background: `${barColour}11` }}>
          {status}
        </span>
      </div>

      <div className="mb-3">
        <div className="mb-1.5 flex justify-between text-[10px] font-mono text-[#525252]">
          <span>Health</span>
          <span style={{ color: barColour }}>{asset.health?.toFixed(0)} / {asset.max_health}</span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-[#1A1A1A]">
          <div className="h-full rounded-full transition-all duration-500" style={{ width: `${Math.max(0, healthFraction * 100)}%`, background: barColour }} />
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {asset.is_critical && <span className="rounded-sm bg-[#1E3A5F] px-1.5 py-0.5 text-[10px] font-mono text-[#93C5FD]">Critical</span>}
        {asset.is_reinforced && <span className="rounded-sm bg-[#14292A] px-1.5 py-0.5 text-[10px] font-mono text-[#6EE7B7]">Reinforced</span>}
        {asset.is_destroyed && <span className="rounded-sm bg-[#3B0000] px-1.5 py-0.5 text-[10px] font-mono text-[#FCA5A5]">Destroyed</span>}
      </div>
    </div>
  )
}

function NationPanel({ nation, simState, previousState, profile, selectedAssetId, coverageMap, previousCoverageMap, endCondition }) {
  const currentCoverage = coverageMap?.[nation] ?? 0
  const prevCoverage = previousCoverageMap?.[nation] ?? 0
  const displacement = (simState?.zones || []).filter((zone) => zone.nation === nation).reduce((sum, zone) => sum + (zone.displaced || 0), 0)
  const stableTurns = simState?.stable_turns_count?.[nation] ?? 0
  const resources = simState?.resources?.[nation]?.stocks || {}
  const previousResources = previousState?.resources?.[nation]?.stocks || {}
  const consequences = simState?.active_consequences?.[nation] || []
  const selectedAsset = (simState?.assets || []).find((asset) => asset.id === selectedAssetId && asset.nation === nation)

  return (
    <div className="space-y-5">
      <EndConditionBanner condition={endCondition} />

      <div className="rounded border border-[#333333] bg-[#212020] p-4">
        <p className="mb-2 text-[11px] font-mono uppercase tracking-[0.14em] text-[#525252]">Service Coverage</p>
        <div className="text-5xl font-mono" style={{ color: colourForCoverage(currentCoverage) }}>{Math.round(currentCoverage * 100)}%</div>
        <div className="mt-1 text-xs font-mono" style={{ color: currentCoverage - prevCoverage >= 0 ? "#22C55E" : "#EF4444" }}>
          {currentCoverage - prevCoverage >= 0 ? "+" : ""}{Math.round((currentCoverage - prevCoverage) * 100)} pts
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="rounded border border-[#333333] bg-[#212020] p-4">
          <p className="mb-2 text-[11px] font-mono uppercase tracking-[0.14em] text-[#525252]">Displaced Persons</p>
          <div className="text-3xl font-mono" style={{ color: displacedColour(displacement) }}>{displacement.toLocaleString()}</div>
        </div>
        <div className="rounded border border-[#333333] bg-[#212020] p-4">
          <p className="mb-2 text-[11px] font-mono uppercase tracking-[0.14em] text-[#525252]">Stable Turns</p>
          <div className="text-3xl font-mono" style={{ color: stableTurnsColour(stableTurns) }}>{stableTurns}</div>
        </div>
      </div>

      <div className="rounded border border-[#333333] bg-[#212020] p-4">
        <p className="mb-3 text-[11px] font-mono uppercase tracking-[0.14em] text-[#525252]">Resource Stocks</p>
        <div className="space-y-3">
          {Object.entries(resources).map(([resource, amount]) => {
            const baseline = Math.max(amount, previousResources[resource] ?? amount, 1)
            const delta = amount - (previousResources[resource] ?? amount)
            const fraction = Math.max(0, Math.min(1, amount / baseline))
            return (
              <div key={resource}>
                <div className="mb-1 flex items-baseline justify-between">
                  <span className="text-[10px] font-mono uppercase tracking-[0.08em] text-[#A3A3A3]">{resource.replaceAll("_", " ")}</span>
                  <span className="font-mono text-[13px] text-[#F5F5F5]">
                    {Math.round(amount)} <span className="text-[11px] text-[#525252]">u</span>{" "}
                    <span style={{ color: delta >= 0 ? "#22C55E" : "#EF4444" }}>{delta >= 0 ? "+" : ""}{Math.round(delta)}</span>
                  </span>
                </div>
                <div className="h-1 overflow-hidden rounded bg-[#1A1A1A]">
                  <div className="h-full transition-[width] duration-400 ease-out" style={{ width: `${Math.max(0, Math.min(100, fraction * 100))}%`, backgroundColor: resourceColour(fraction) }} />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="rounded border border-[#333333] bg-[#212020] p-4">
        <p className="mb-3 text-[11px] font-mono uppercase tracking-[0.14em] text-[#525252]">Active Consequences</p>
        <div className="flex flex-wrap gap-2">
          {consequences.length === 0 ? (
            <div style={{ display: "flex", alignItems: "center", gap: "6px", padding: "6px 0" }}>
              <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#22C55E" }} />
              <span style={{ fontFamily: "monospace", fontSize: "10px", letterSpacing: "0.08em", textTransform: "uppercase", color: "#22C55E" }}>
                All systems nominal
              </span>
            </div>
          ) : null}
          {consequences.map((tag) => {
            const tone = consequenceTone(tag)
            return (
              <span key={tag} className="rounded px-2 py-1 text-[10px] font-medium uppercase tracking-[0.04em]" style={{ backgroundColor: tone.bg, color: tone.fg }}>
                {tag.replaceAll("_", " ")}
              </span>
            )
          })}
        </div>
      </div>

      <AssetDetail asset={selectedAsset} />

      {profile ? <CountryProfileSummary profile={profile} /> : null}
    </div>
  )
}

export default function KpiPanel({ simState, previousState, profiles, selectedAssetId, coverageMap, previousCoverageMap, eventLog, endConditions, lastNarrative }) {
  const [tab, setTab] = useState("Auria")
  const nations = useNationDisplayNames()

  const tabs = [
    { id: "Auria", label: nations.find((item) => item.internal === "Auria")?.display ?? "Auria", accent: "#3B82F6" },
    { id: "Boros", label: nations.find((item) => item.internal === "Boros")?.display ?? "Boros", accent: "#F59E0B" },
    { id: "Events", label: "Events", accent: "#525252" },
  ]

  return (
    <div className="h-full rounded border border-[#333333] bg-[#0A0A0A] p-4">
      <div className="mb-4 flex gap-4 border-b border-[#1F1F1F]">
        {tabs.map((item) => (
          <button key={item.id} onClick={() => setTab(item.id)} className="pb-3 text-xs font-mono uppercase tracking-[0.14em] transition-colors" style={{ color: tab === item.id ? "#F5F5F5" : "#525252", borderBottom: tab === item.id ? `2px solid ${item.accent}` : "2px solid transparent" }}>
            {item.label}
          </button>
        ))}
      </div>

      {tab === "Events" ? (
        <div className="flex h-[600px] flex-col p-0">
          <EventLog events={eventLog} lastNarrative={lastNarrative} lastTurn={simState?.turn ?? 0} />
        </div>
      ) : (
        <NationPanel nation={tab} simState={simState} previousState={previousState} profile={profiles?.[tab]} selectedAssetId={selectedAssetId} coverageMap={coverageMap} previousCoverageMap={previousCoverageMap} endCondition={endConditions?.[tab]} />
      )}
    </div>
  )
}
