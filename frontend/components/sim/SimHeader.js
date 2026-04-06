"use client"

export default function SimHeader({ scenarioName, turn, maxTurns, coverage = {} }) {
  const coverageA = coverage?.Auria ?? 1
  const coverageB = coverage?.Boros ?? 1
  const bothStable = coverageA > 0.7 && coverageB > 0.7
  const anyCritical = coverageA < 0.5 || coverageB < 0.5

  let dotColour = "#F59E0B"
  let dotLabel = "Active"
  if (bothStable) {
    dotColour = "#22C55E"
    dotLabel = "Stable"
  } else if (anyCritical) {
    dotColour = "#EF4444"
    dotLabel = "Critical"
  }

  return (
    <div className="sticky top-0 z-30 h-12 border-b border-[#1F1F1F] bg-[#0A0A0A]/90 backdrop-blur px-6 flex items-center justify-between">
      <div className="flex items-center gap-3 min-w-0">
        <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#525252]">ResilienceSim</span>
        <span className="text-[#333333]">|</span>
        <span className="text-[15px] font-semibold text-[#F5F5F5] tracking-tight truncate">{scenarioName || "No scenario loaded"}</span>
      </div>
      <div className="flex items-center gap-4">
        <span className="font-mono text-[13px] text-[#A3A3A3]">
          Turn <span className="text-[#F5F5F5]">{turn ?? 0}</span> / {maxTurns ?? 60}
        </span>
        <div className="flex items-center gap-2">
          <span className="w-[7px] h-[7px] rounded-full" style={{ backgroundColor: dotColour }} />
          <span className="text-xs" style={{ color: dotColour }}>{dotLabel}</span>
        </div>
      </div>
    </div>
  )
}
