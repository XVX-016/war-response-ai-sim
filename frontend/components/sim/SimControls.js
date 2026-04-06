"use client"

import TurnControl from "@/components/sim/TurnControl"

export default function SimControls({
  scenarios,
  scenarioPath,
  simState,
  isRunning,
  isTerminal,
  autoStep,
  stepDelay,
  nationFilter,
  turnPhase,
  onScenarioChange,
  onProposeTurn,
  onReset,
  onAutoStepChange,
  onStepDelayChange,
  onNationFilterChange,
}) {
  const turn = simState?.turn ?? 0
  const maxTurns = simState?.max_turns ?? 60

  return (
    <div className="sticky top-16 space-y-5 rounded border border-[#333333] bg-[#0A0A0A] p-4">
      <div>
        <p className="mb-2 text-[11px] font-mono uppercase tracking-[0.14em] text-[#525252]">Scenario</p>
        <select value={scenarioPath || ""} onChange={(e) => onScenarioChange(e.target.value)} className="w-full rounded border border-[#333333] bg-[#1A1A1A] px-3 py-2 text-sm text-[#F5F5F5] outline-none">
          <option value="">Select a scenario</option>
          {scenarios.map((scenario) => (
            <option key={scenario.path} value={scenario.path}>{scenario.name}</option>
          ))}
        </select>
      </div>

      <div style={{ marginBottom: "16px" }}>
        <div style={{ fontFamily: "Space Mono, monospace", fontSize: "9px", letterSpacing: "0.15em", textTransform: "uppercase", color: "#525252", marginBottom: "4px" }}>
          Turn Counter
        </div>
        <div style={{ fontFamily: "Space Mono, monospace", fontSize: "28px", fontWeight: 500, color: "#F5F5F5", letterSpacing: "-0.02em", lineHeight: 1 }}>
          {turn}
          <span style={{ color: "#333333", fontSize: "16px" }}> / {maxTurns}</span>
        </div>
        <div style={{ height: "2px", background: "#1A1A1A", borderRadius: "1px", marginTop: "8px", overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${(turn / maxTurns) * 100}%`, background: "#3B82F6", transition: "width 300ms ease" }} />
        </div>
      </div>

      <div className="space-y-3">
        <TurnControl
          turnPhase={turnPhase}
          isRunning={isRunning}
          isTerminal={isTerminal}
          disabled={!simState || turnPhase !== "idle"}
          onProposeTurn={onProposeTurn}
        />
        <button onClick={onReset} disabled={!scenarioPath || isRunning} className="w-full rounded border border-[#333333] px-4 py-2 text-xs font-mono uppercase tracking-[0.15em] text-[#A3A3A3] disabled:opacity-40">
          Reset Scenario
        </button>
      </div>

      <div>
        <label className="mb-2 flex items-center justify-between text-sm text-[#A3A3A3]">
          <span>Auto-step</span>
          <input type="checkbox" checked={autoStep} onChange={(e) => onAutoStepChange(e.target.checked)} disabled={!simState || isTerminal} />
        </label>
        <input type="range" min="500" max="3000" step="250" value={stepDelay} onChange={(e) => onStepDelayChange(Number(e.target.value))} className="w-full accent-[#3B82F6]" />
        <div className="mt-1 font-mono text-xs text-[#525252]">{(stepDelay / 1000).toFixed(2)}s delay</div>
      </div>

      <div>
        <p className="mb-2 text-[11px] font-mono uppercase tracking-[0.14em] text-[#525252]">Nation Filter</p>
        <div className="flex flex-wrap gap-2">
          {["All", "Auria", "Boros"].map((nation) => (
            <button key={nation} onClick={() => onNationFilterChange(nation)} className={`rounded border px-3 py-1 text-xs font-mono uppercase tracking-[0.12em] ${nationFilter === nation ? "border-[#3B82F6] text-white" : "border-[#333333] text-[#525252]"}`}>
              {nation}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
