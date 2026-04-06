"use client"

export default function TurnControl({ turnPhase, isRunning, isTerminal, disabled, onProposeTurn }) {
  const label =
    turnPhase === "proposing"
      ? "Fetching proposal..."
      : turnPhase === "reviewing"
        ? "Review proposal ↓"
        : isTerminal
          ? "Simulation Ended"
          : "Propose Turn"

  return (
    <button
      onClick={onProposeTurn}
      disabled={disabled || isTerminal}
      style={{
        width: "100%",
        padding: "10px",
        background: turnPhase === "proposing" || isRunning ? "#1D4ED8" : "#3B82F6",
        border: "none",
        borderRadius: "4px",
        color: "#ffffff",
        fontFamily: "Space Mono, monospace",
        fontSize: "11px",
        letterSpacing: "0.12em",
        textTransform: "uppercase",
        cursor: disabled || isTerminal ? "not-allowed" : "pointer",
        opacity: isTerminal ? 0.35 : disabled ? 0.6 : 1,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "8px",
        transition: "background 150ms ease",
      }}
    >
      {isRunning ? <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#ffffff", animation: "pulse 1s ease infinite" }} /> : null}
      {label}
    </button>
  )
}
