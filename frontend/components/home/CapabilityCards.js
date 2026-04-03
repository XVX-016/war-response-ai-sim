const CAPS = [
  {
    code: "CF",
    title: "Cascade Failure Engine",
    desc: "Dependency-graph propagation across power, water, hospitals, and transport. Each degraded asset penalises its dependents every turn.",
    tags: ["Dependency graph", "Turn-based propagation", "8 asset types"],
  },
  {
    code: "AI",
    title: "Multi-Agent AI",
    desc: "Rule-based agents autonomously manage recovery under resource constraints. Country profiles scale action budgets, repair capacity, and alliance resupply.",
    tags: ["Rule-based policy", "Country parameterisation", "Resource modelling"],
  },
  {
    code: "CV",
    title: "Vision Pipeline",
    desc: "YOLOv8 detects civilian infrastructure from aerial imagery. Detections seed scenario JSON files automatically.",
    tags: ["YOLOv8 fine-tuned", "xView dataset", "Scenario annotation"],
  },
]

export default function CapabilityCards() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {CAPS.map((cap) => (
        <div key={cap.title} className="border border-[#333333] rounded p-8 hover:border-[#525252] transition-colors bg-transparent group">
          <div className="font-mono text-[10px] tracking-[0.15em] text-[#3B82F6] border border-[#333333] rounded px-2 py-1 inline-block mb-6 w-fit group-hover:border-[#3B82F6] transition-colors">
            {cap.code}
          </div>
          <p className="text-xs font-mono tracking-[0.15em] uppercase text-[#525252] mb-2 group-hover:text-[#3B82F6] transition-colors">{cap.title}</p>
          <p className="text-sm text-[#A3A3A3] mb-6 leading-relaxed">{cap.desc}</p>
          <ul className="space-y-1">
            {cap.tags.map((tag) => (
              <li key={tag} className="text-xs font-mono text-[#525252] flex items-center gap-2">
                <span className="w-1 h-1 rounded-full bg-[#333333]" />
                {tag}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}
