"use client"

import { useState } from "react"
import { useSimStore } from "@/store/simStore"

const ACTION_LABELS = {
  repair: "Repair",
  reinforce: "Reinforce",
  restore_power: "Restore Power",
  evacuate: "Evacuate",
  allocate_supplies: "Allocate Supplies",
  reroute: "Reroute",
  inspect: "Inspect",
}

export default function ActionProposal({ onExecute, onCancel }) {
  const proposedActions = useSimStore((s) => s.proposedActions)
  const actionReasonings = useSimStore((s) => s.actionReasonings)
  const simState = useSimStore((s) => s.simState)
  const [overrides, setOverrides] = useState({})

  if (proposedActions.length === 0) {
    return (
      <div style={{ border: "1px solid #333333", borderRadius: "4px", padding: "16px", background: "#212020", textAlign: "center" }}>
        <p style={{ fontFamily: "DM Sans, sans-serif", fontSize: "11px", color: "#525252", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          No actions proposed - agents are passing this turn
        </p>
        <button onClick={() => onExecute([])} style={primaryBtn}>
          Advance Turn (No Actions)
        </button>
      </div>
    )
  }

  function getStatus(index) {
    return overrides[index] ?? "accept"
  }

  function toggle(index) {
    setOverrides((prev) => ({
      ...prev,
      [index]: prev[index] === "skip" ? "accept" : "skip",
    }))
  }

  function handleExecute() {
    const finalActions = proposedActions.filter((_, index) => getStatus(index) === "accept")
    onExecute(finalActions)
  }

  const acceptedCount = proposedActions.filter((_, index) => getStatus(index) === "accept").length

  return (
    <div style={{ border: "1px solid #1D3251", borderRadius: "4px", background: "#131B26", overflow: "hidden" }}>
      <div style={{ background: "#1D3251", padding: "10px 14px", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid #263F6B" }}>
        <div>
          <span style={{ fontFamily: "DM Mono, monospace", fontSize: "9px", letterSpacing: "0.15em", textTransform: "uppercase", color: "#3B82F6" }}>
            Agent Proposal
          </span>
          <span style={{ fontFamily: "DM Sans, sans-serif", fontSize: "12px", color: "#F5F5F5", marginLeft: "12px" }}>
            {proposedActions.length} actions · {acceptedCount} accepted
          </span>
        </div>
        <span style={{ fontFamily: "DM Sans, sans-serif", fontSize: "10px", color: "#525252", letterSpacing: "0.04em" }}>
          Click any action to skip it
        </span>
      </div>

      <div style={{ padding: "8px" }}>
        {proposedActions.map((action, index) => {
          const reasoning = actionReasonings[index]
          const accepted = getStatus(index) === "accept"
          const asset = action.target_asset_id ? simState?.assets?.find((item) => item.id === action.target_asset_id) : null
          const zone = action.target_zone_id ? simState?.zones?.find((item) => item.id === action.target_zone_id) : null
          const targetName = asset?.name || zone?.name || action.target_asset_id || action.target_zone_id || "-"
          const nationColour = action.actor_nation === simState?.nations?.[0] ? "#3B82F6" : "#F59E0B"

          return (
            <div
              key={`${action.actor_nation}-${action.action_type}-${index}`}
              onClick={() => toggle(index)}
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "10px",
                padding: "10px",
                marginBottom: "4px",
                background: accepted ? "#131F14" : "#1A1A1A",
                borderRadius: "3px",
                border: accepted ? "1px solid #1A3320" : "1px solid #2D2C2C",
                cursor: "pointer",
                opacity: accepted ? 1 : 0.45,
                transition: "all 150ms ease",
              }}
            >
              <div style={{ width: "16px", height: "16px", borderRadius: "2px", border: `1px solid ${accepted ? "#22C55E" : "#333333"}`, background: accepted ? "#22C55E" : "transparent", flexShrink: 0, marginTop: "2px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                {accepted ? <span style={{ color: "#000", fontSize: "10px", fontWeight: 700 }}>✓</span> : null}
              </div>

              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", gap: "8px", marginBottom: "4px", alignItems: "center", flexWrap: "wrap" }}>
                  <span style={{ fontFamily: "DM Mono, monospace", fontSize: "10px", letterSpacing: "0.08em", textTransform: "uppercase", color: nationColour }}>
                    {action.actor_nation}
                  </span>
                  <span style={{ fontFamily: "DM Sans, sans-serif", fontSize: "13px", color: "#F5F5F5", fontWeight: 600 }}>
                    {ACTION_LABELS[action.action_type] || action.action_type}
                  </span>
                  <span style={{ fontFamily: "DM Sans, sans-serif", fontSize: "12px", color: "#A3A3A3" }}>
                    -> {targetName}
                  </span>
                </div>

                {reasoning?.reason ? (
                  <div style={{ fontFamily: "DM Sans, sans-serif", fontSize: "12px", fontWeight: 300, color: "#6B7280", lineHeight: "1.4" }}>
                    {reasoning.reason}
                  </div>
                ) : null}
              </div>
            </div>
          )
        })}
      </div>

      <div style={{ padding: "10px 14px", borderTop: "1px solid #1F1F1F", display: "flex", gap: "8px", justifyContent: "flex-end" }}>
        <button onClick={onCancel} style={{ padding: "8px 16px", background: "#212020", border: "1px solid #333333", borderRadius: "4px", color: "#A3A3A3", fontFamily: "DM Sans, sans-serif", fontSize: "12px", letterSpacing: "0.04em", cursor: "pointer" }}>
          Cancel
        </button>
        <button onClick={handleExecute} style={{ padding: "8px 20px", background: "#22C55E", border: "1px solid #22C55E", borderRadius: "4px", color: "#000000", fontFamily: "DM Sans, sans-serif", fontSize: "12px", fontWeight: 600, letterSpacing: "0.04em", cursor: "pointer" }}>
          Execute {acceptedCount} Action{acceptedCount !== 1 ? "s" : ""}
        </button>
      </div>
    </div>
  )
}

const primaryBtn = {
  marginTop: "12px",
  padding: "8px 20px",
  background: "#3B82F6",
  border: "none",
  borderRadius: "4px",
  color: "#ffffff",
  fontFamily: "DM Sans, sans-serif",
  fontSize: "12px",
  fontWeight: 600,
  letterSpacing: "0.04em",
  cursor: "pointer",
  display: "block",
  marginInline: "auto",
}
