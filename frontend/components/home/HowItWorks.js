const STEPS = [
  { n: "01", title: "Configure Nations", desc: "Set GDP, military strength, population, resources, terrain, and alliance factors for each fictional nation." },
  { n: "02", title: "Load Scenario", desc: "Choose from hand-crafted crisis scenarios or generate one via the scenario builder." },
  { n: "03", title: "Run Simulation", desc: "AI agents manage recovery across 60 turns. Cascading consequences fire each turn based on asset dependencies." },
  { n: "04", title: "Analyse Results", desc: "Review service coverage timeline, displacement counts, event log, and optional AI-generated humanitarian summaries." },
]

export default function HowItWorks() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6 md:gap-0">
      {STEPS.map((s, i) => (
        <div key={s.n} className="relative flex flex-col">
          <div className="relative z-10 pr-8">
            <span className="font-mono text-xs text-[#3B82F6] tracking-widest mb-3 block">{s.n}</span>
            <h3 className="text-sm font-semibold text-[#F5F5F5] mb-2 tracking-tight">{s.title}</h3>
            <p className="text-xs text-[#525252] leading-relaxed">{s.desc}</p>
          </div>
        </div>
      ))}
    </div>
  )
}
