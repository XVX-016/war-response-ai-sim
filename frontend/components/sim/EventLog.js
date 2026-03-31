"use client"

import { useMemo, useState } from "react"

const EVENT_TYPE_BG = {
  action_complete: "#1E3A5F",
  action_queued: "#1E3A5F",
  action_rejected: "#3B0000",
  consequence: "#3B2500",
  exogenous: "#2D1B69",
  alliance_resupply: "#14292A",
  end_condition: "#14291A",
}

const SEVERITY_BORDER = {
  critical: "#EF4444",
  warning: "#F59E0B",
  info: "#3B82F6",
}

function normaliseEvents(events) {
  return [...(events || [])].sort((a, b) => b.turn - a.turn)
}

export default function EventLog({ events }) {
  const [filter, setFilter] = useState("All")

  const filtered = useMemo(() => {
    return normaliseEvents(events).filter((event) => {
      if (filter === "Critical") return event.severity === "critical"
      if (filter === "Warnings") return event.severity === "warning"
      if (filter === "Actions") return String(event.event_type || "").startsWith("action_")
      return true
    })
  }, [events, filter])

  const filters = ["All", "Critical", "Warnings", "Actions"]

  return (
    <div>
      <div className="flex gap-2 mb-4 flex-wrap">
        {filters.map((name) => (
          <button
            key={name}
            onClick={() => setFilter(name)}
            className={`px-3 py-1 text-[11px] uppercase font-mono tracking-[0.15em] rounded border transition-colors ${filter === name ? "text-white border-[#3B82F6] bg-[#212020]" : "text-[#525252] border-[#333333] hover:text-[#A3A3A3]"}`}
          >
            {name}
          </button>
        ))}
      </div>
      <div className="max-h-[560px] overflow-y-auto pr-1">
        {filtered.length === 0 ? <div className="text-[#525252] font-mono text-sm">No events yet.</div> : null}
        {filtered.map((event, index) => {
          const evtType = event.event_type || "info"
          const borderColour = SEVERITY_BORDER[event.severity] || "#333333"
          const tagBg = EVENT_TYPE_BG[evtType] || "#1A1A1A"
          return (
            <div key={`${event.turn}-${index}-${evtType}`} className="mb-1 rounded-r-sm bg-[#0A0A0A] px-3 py-2 hover:bg-[#212020]" style={{ borderLeft: `3px solid ${borderColour}` }}>
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-[10px] text-[#525252] min-w-[32px]">T{String(event.turn).padStart(2, "0")}</span>
                <span className="px-1.5 py-[1px] rounded-sm text-[10px] uppercase tracking-[0.05em] text-[#A3A3A3]" style={{ backgroundColor: tagBg }}>
                  {evtType.replaceAll("_", " ")}
                </span>
              </div>
              <div className="text-[12px] text-[#D4D4D4] leading-relaxed">{event.description}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
