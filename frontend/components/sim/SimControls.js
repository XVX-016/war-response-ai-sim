"use client"

export default function SimControls({
  scenarios,
  scenarioPath,
  simState,
  isRunning,
  autoStep,
  stepDelay,
  nationFilter,
  onScenarioChange,
  onAdvance,
  onReset,
  onAutoStepChange,
  onStepDelayChange,
  onNationFilterChange,
}) {
  return (
    <div className="border border-[#333333] rounded bg-[#0A0A0A] p-4 space-y-5 sticky top-16">
      <div>
        <p className="text-[11px] uppercase tracking-[0.14em] font-mono text-[#525252] mb-2">Scenario</p>
        <select value={scenarioPath || ""} onChange={(e) => onScenarioChange(e.target.value)} className="w-full bg-[#1A1A1A] border border-[#333333] rounded px-3 py-2 text-sm text-[#F5F5F5] outline-none">
          <option value="">Select a scenario</option>
          {scenarios.map((scenario) => (
            <option key={scenario.path} value={scenario.path}>{scenario.name}</option>
          ))}
        </select>
      </div>

      <div>
        <p className="text-[11px] uppercase tracking-[0.14em] font-mono text-[#525252] mb-1">Turn Counter</p>
        <div className="font-mono text-[#F5F5F5] text-lg">{simState?.turn ?? 0} / {simState?.max_turns ?? 60}</div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <button onClick={onAdvance} disabled={isRunning || simState?.is_terminal || !simState} className="px-4 py-2 rounded border border-[#3B82F6] bg-[#3B82F6] text-white text-xs font-mono uppercase tracking-[0.15em] disabled:opacity-40">
          Advance Turn
        </button>
        <button onClick={onReset} disabled={!scenarioPath || isRunning} className="px-4 py-2 rounded border border-[#333333] text-[#A3A3A3] text-xs font-mono uppercase tracking-[0.15em] disabled:opacity-40">
          Reset
        </button>
      </div>

      <div>
        <label className="flex items-center justify-between text-sm text-[#A3A3A3] mb-2">
          <span>Auto-step</span>
          <input type="checkbox" checked={autoStep} onChange={(e) => onAutoStepChange(e.target.checked)} disabled={!simState || simState?.is_terminal} />
        </label>
        <input type="range" min="500" max="3000" step="250" value={stepDelay} onChange={(e) => onStepDelayChange(Number(e.target.value))} className="w-full accent-[#3B82F6]" />
        <div className="font-mono text-xs text-[#525252] mt-1">{(stepDelay / 1000).toFixed(2)}s delay</div>
      </div>

      <div>
        <p className="text-[11px] uppercase tracking-[0.14em] font-mono text-[#525252] mb-2">Nation Filter</p>
        <div className="flex gap-2 flex-wrap">
          {["All", "Auria", "Boros"].map((nation) => (
            <button key={nation} onClick={() => onNationFilterChange(nation)} className={`px-3 py-1 rounded border text-xs font-mono uppercase tracking-[0.12em] ${nationFilter === nation ? "border-[#3B82F6] text-white" : "border-[#333333] text-[#525252]"}`}>
              {nation}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
