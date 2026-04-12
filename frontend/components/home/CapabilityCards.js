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
        <div key={cap.title} className="border border-[#333333] rounded p-5 md:p-8 hover:border-[rgba(59,130,246,0.4)] transition-colors bg-transparent">
          <p
            style={{
              fontFamily: "DM Sans, system-ui, sans-serif",
              fontSize: "11px",
              fontWeight: 600,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "#A3A3A3",
              marginBottom: "10px",
            }}
          >
            {cap.title}
          </p>
          <p className="text-sm text-[#A3A3A3] mb-6" style={{ fontWeight: 300, lineHeight: 1.65 }}>{cap.desc}</p>
          <div className="space-y-1">
            {cap.tags.map((tag) => (
              <div
                key={tag}
                style={{
                  paddingLeft: "8px",
                  borderLeft: "1px solid #333333",
                  marginBottom: "4px",
                  fontFamily: "DM Sans, sans-serif",
                  fontSize: "12px",
                  fontWeight: 300,
                  color: "#525252",
                }}
              >
                {tag}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
