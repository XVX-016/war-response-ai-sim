"use client"

import { useState } from "react"
import { useSimStore } from "@/store/simStore"

const FILTERS = ["All", "Critical", "Warnings", "Actions", "Consequences"]

const EVENT_TYPE_COLOURS = {
  action_complete: { bg: "#1E3A5F", text: "#93C5FD" },
  action_queued: { bg: "#1E3A5F", text: "#93C5FD" },
  action_rejected: { bg: "#3B0000", text: "#FCA5A5" },
  consequence: { bg: "#3B2500", text: "#FCD34D" },
  exogenous: { bg: "#2D1B69", text: "#C4B5FD" },
  alliance_resupply: { bg: "#14292A", text: "#6EE7B7" },
  end_condition: { bg: "#14291A", text: "#86EFAC" },
  dependency_penalty: { bg: "#2D1A00", text: "#FB923C" },
  displacement: { bg: "#3B0000", text: "#FCA5A5" },
  mortality_risk: { bg: "#3B0000", text: "#FCA5A5" },
  default: { bg: "#1A1A1A", text: "#A3A3A3" },
}

const SEVERITY_BORDER = {
  critical: "#EF4444",
  warning: "#F59E0B",
  info: "#3B82F6",
}

function fixEncoding(str) {
  if (!str) return ""
  try {
    return decodeURIComponent(escape(str))
  } catch {
    return str.replace(/â€¦/g, "...").replace(/Â·/g, "·").replace(/â†’/g, "->")
  }
}

export default function EventLog({ events = [] }) {
  const [filter, setFilter] = useState("All")
  const lastNarrative = useSimStore((s) => s.lastNarrative)
  const narrativeHistory = useSimStore((s) => s.narrativeHistory)
  const lastTurn = useSimStore((s) => s.simState?.turn ?? 0)

  const filtered = events
    .slice()
    .reverse()
    .filter((event) => {
      if (filter === "All") return true
      if (filter === "Critical") return event.severity === "critical"
      if (filter === "Warnings") return event.severity === "warning"
      if (filter === "Actions") return event.event_type?.startsWith("action_")
      if (filter === "Consequences") return event.event_type === "consequence"
      return true
    })

  return (
    <div className="flex h-full flex-col">
      {lastNarrative ? (
        <div style={{ borderLeft: "3px solid #3B82F6", background: "#1A2233", borderRadius: "0 4px 4px 0", padding: "12px 14px", marginBottom: "16px" }}>
          <div style={{ fontFamily: "DM Mono, monospace", fontSize: "9px", letterSpacing: "0.12em", textTransform: "uppercase", color: "#3B82F6", marginBottom: "6px" }}>
            AI Summary · Turn {lastTurn}
          </div>
          <p style={{ fontFamily: "DM Sans, sans-serif", fontSize: "12px", fontWeight: 300, color: "#D4D4D4", lineHeight: "1.6", fontStyle: "italic" }}>
            {fixEncoding(lastNarrative)}
          </p>
        </div>
      ) : null}

      {narrativeHistory.length > 1 ? (
        <details style={{ marginBottom: "12px" }}>
          <summary style={{ fontSize: "10px", fontFamily: "DM Mono, monospace", color: "#525252", cursor: "pointer", letterSpacing: "0.08em", textTransform: "uppercase" }}>
            Previous summaries ({narrativeHistory.length - 1})
          </summary>
          <div style={{ marginTop: "8px" }}>
            {[...narrativeHistory].reverse().slice(1).map(({ turn, text }) => (
              <div key={`${turn}-${text.slice(0, 12)}`} style={{ padding: "8px 0", borderBottom: "1px solid #1F1F1F", fontSize: "11px", color: "#525252", lineHeight: "1.5", fontFamily: "DM Sans, sans-serif", fontWeight: 300 }}>
                <span style={{ fontFamily: "DM Mono, monospace", fontSize: "9px", color: "#333333", marginRight: "8px" }}>
                  T{String(turn).padStart(2, "0")}
                </span>
                {fixEncoding(text)}
              </div>
            ))}
          </div>
        </details>
      ) : null}

      <div className="mb-3 flex flex-wrap gap-1">
        {FILTERS.map((item) => (
          <button
            key={item}
            onClick={() => setFilter(item)}
            className={`rounded border px-2 py-1 text-[10px] uppercase transition-colors ${
              filter === item ? "border-[#3B82F6] bg-[#212020] text-[#F5F5F5]" : "border-[#333333] bg-transparent text-[#525252]"
            }`}
            style={{ fontFamily: "DM Mono, monospace", letterSpacing: "0.08em" }}
          >
            {item}
          </button>
        ))}
        <span className="ml-auto self-center text-[10px] text-[#525252]" style={{ fontFamily: "DM Mono, monospace" }}>
          {filtered.length} events
        </span>
      </div>

      {!lastNarrative && narrativeHistory.length === 0 ? (
        <p style={{ fontSize: "10px", fontFamily: "DM Mono, monospace", color: "#333333", marginBottom: "12px", letterSpacing: "0.06em" }}>
          Set ANTHROPIC_API_KEY in .env to enable AI turn summaries
        </p>
      ) : null}

      {filtered.length === 0 ? (
        <div className="flex flex-1 items-center justify-center">
          <p className="text-xs text-[#525252]" style={{ fontFamily: "DM Sans, sans-serif", fontWeight: 300 }}>
            {events.length === 0 ? "No events yet - advance a turn to begin" : "No events match this filter"}
          </p>
        </div>
      ) : null}

      <div className="flex-1 space-y-1 overflow-y-auto">
        {filtered.map((event, index) => {
          const typeStyle = EVENT_TYPE_COLOURS[event.event_type] ?? EVENT_TYPE_COLOURS.default
          const borderCol = SEVERITY_BORDER[event.severity] ?? SEVERITY_BORDER.info
          return (
            <div key={`${event.turn ?? 0}-${index}-${event.event_type ?? "event"}`} className="cursor-default flex flex-col gap-1 bg-[#0A0A0A] px-3 py-2 transition-colors hover:bg-[#151515]" style={{ borderLeft: `3px solid ${borderCol}` }}>
              <div className="flex items-center gap-2">
                <span style={{ minWidth: "28px", fontFamily: "DM Mono, monospace", fontSize: "10px", color: "#525252", background: "#1A1A1A", border: "1px solid #2D2C2C", borderRadius: "3px", padding: "1px 4px" }}>
                  T{String(event.turn ?? 0).padStart(2, "0")}
                </span>
                <span style={{ borderRadius: "3px", padding: "2px 6px", fontSize: "10px", fontFamily: "DM Sans, sans-serif", fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase", background: typeStyle.bg, color: typeStyle.text }}>
                  {(event.event_type ?? "event").replace(/_/g, " ")}
                </span>
                {event.nation ? <span style={{ fontFamily: "DM Sans, sans-serif", fontSize: "10px", fontWeight: 300, color: "#525252" }}>{event.nation}</span> : null}
              </div>
              <p style={{ paddingLeft: "36px", fontFamily: "DM Sans, sans-serif", fontWeight: 300, fontSize: "12px", color: "#D4D4D4", lineHeight: 1.5 }}>
                {fixEncoding(event.description)}
              </p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
