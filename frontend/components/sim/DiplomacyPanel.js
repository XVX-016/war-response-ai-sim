"use client"

import { useSimStore } from "@/store/simStore"
import { useNationDisplayNames } from "@/lib/nations"

function FactorBar({ label, value, colour }) {
  const pct = Math.round(value * 100)
  const barColour = pct > 60 ? "#22C55E" : pct > 30 ? "#F59E0B" : "#EF4444"
  return (
    <div style={{ marginBottom: "6px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "3px" }}>
        <span style={{ fontFamily: "DM Sans, sans-serif", fontSize: "10px", letterSpacing: "0.04em", textTransform: "uppercase", color: "#525252" }}>
          {label}
        </span>
        <span style={{ fontFamily: "DM Mono, monospace", fontSize: "10px", color: colour }}>{value.toFixed(3)}</span>
      </div>
      <div style={{ height: "3px", background: "#1A1A1A", borderRadius: "1px", overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: barColour, transition: "width 400ms ease" }} />
      </div>
    </div>
  )
}

function Badge({ label, type }) {
  const config = {
    trade: { background: "#1A2E1A", color: "#22C55E", border: "1px solid #1F3D1F" },
    tension: { background: "#2E1A1A", color: "#F59E0B", border: "1px solid #3D2A1A" },
    sanctions: { background: "#2E0000", color: "#EF4444", border: "1px solid #4D0000" },
    aid: { background: "#1A2E1A", color: "#22C55E", border: "1px solid #1F3D1F" },
  }[type]

  return (
    <span
      style={{
        fontFamily: "DM Sans, sans-serif",
        fontSize: "10px",
        fontWeight: 500,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        padding: "2px 6px",
        borderRadius: "3px",
        ...config,
      }}
    >
      {label}
    </span>
  )
}

export default function DiplomacyPanel() {
  const simState = useSimStore((s) => s.simState)
  const displayNames = useNationDisplayNames()
  if (!simState?.diplomatic_state) return null

  const dip = simState.diplomatic_state
  const nations = simState.nations ?? []
  const relation = Object.values(dip.relations ?? {})[0]

  return (
    <div style={{ border: "1px solid #2D2C2C", borderRadius: "4px", padding: "16px", marginTop: "12px", background: "#151515" }}>
      <div style={{ fontFamily: "DM Mono, monospace", fontSize: "9px", letterSpacing: "0.15em", textTransform: "uppercase", color: "#525252", marginBottom: "12px" }}>
        Diplomatic State
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "16px" }}>
        {nations.map((nation, index) => {
          const gdp = dip.gdp_index?.[nation] ?? 0.5
          const alliance = dip.alliance_strength?.[nation] ?? 0.5
          const colour = index === 0 ? "#3B82F6" : "#F59E0B"
          const display = displayNames.find((item) => item.internal === nation)?.display ?? nation

          return (
            <div key={nation} style={{ background: "#1C1C1C", borderRadius: "4px", padding: "10px", borderLeft: `3px solid ${colour}` }}>
              <div style={{ fontFamily: "DM Mono, monospace", fontSize: "10px", color: colour, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "8px" }}>
                {display}
              </div>
              <FactorBar label="GDP Index" value={gdp} colour={colour} />
              <FactorBar label="Alliance" value={alliance} colour={colour} />
            </div>
          )
        })}
      </div>

      {relation ? (
        <div style={{ marginBottom: "12px" }}>
          <div style={{ fontFamily: "DM Mono, monospace", fontSize: "9px", letterSpacing: "0.1em", textTransform: "uppercase", color: "#525252", marginBottom: "8px" }}>
            {(displayNames[0]?.display ?? nations[0])} ↔ {(displayNames[1]?.display ?? nations[1])}
          </div>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <Badge label={`Trade ${(relation.trade_volume * 100).toFixed(0)}%`} type="trade" />
            <Badge label={`Tension ${(relation.tension * 100).toFixed(0)}%`} type="tension" />
            {relation.sanctions_active ? <Badge label="Sanctions Active" type="sanctions" /> : null}
            {relation.aid_active ? <Badge label="Aid Corridor Open" type="aid" /> : null}
          </div>
        </div>
      ) : null}

      {dip.events_this_turn?.length > 0 ? (
        <div>
          <div style={{ fontFamily: "DM Mono, monospace", fontSize: "9px", letterSpacing: "0.1em", textTransform: "uppercase", color: "#525252", marginBottom: "6px" }}>
            This turn
          </div>
          {dip.events_this_turn.slice(0, 4).map((evt, index) => (
            <div key={index} style={{ fontFamily: "DM Sans, sans-serif", fontSize: "11px", fontWeight: 300, color: "#A3A3A3", padding: "3px 0", borderBottom: "1px solid #1F1F1F" }}>
              {evt}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}
