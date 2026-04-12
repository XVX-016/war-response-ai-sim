"use client"

export default function SimHeader({ scenarioName, turn, maxTurns }) {
  return (
    <div className="sticky top-0 z-30 h-12 border-b border-[#1F1F1F] bg-[#0A0A0A]/90 backdrop-blur px-3 md:px-6 flex items-center justify-between">
      <div className="flex items-center gap-3 min-w-0">
        <span className="text-[13px] sm:text-[15px] font-semibold text-[#F5F5F5] tracking-tight truncate">{scenarioName || "No scenario loaded"}</span>
      </div>
      <span style={{ fontFamily: "DM Mono, monospace", fontSize: "13px", color: "#A3A3A3", letterSpacing: "-0.01em" }}>
        Turn <span style={{ color: "#F5F5F5" }}>{turn ?? 0}</span> / {maxTurns ?? 60}
      </span>
    </div>
  )
}
