"use client"
import { motion, AnimatePresence } from "framer-motion"
import { useSimStore } from "@/store/simStore"
import { useRouter } from "next/navigation"

export default function EndScreen({ onRestart }) {
  const simState = useSimStore((s) => s.simState)
  const history = useSimStore((s) => s.history)
  const isTerminal = simState?.is_terminal ?? false
  const endConditions = simState?.end_conditions_met ?? {}
  const router = useRouter()

  const nations = simState?.nations ?? []
  const allStabilised = nations.every((nation) => endConditions[nation] === "stabilised")
  const anyCollapsed = nations.some((nation) => endConditions[nation] === "collapsed")

  const outcome = allStabilised
    ? { label: "STABILISED", colour: "#22C55E", sub: "Infrastructure resilience achieved" }
    : anyCollapsed
      ? { label: "COLLAPSED", colour: "#EF4444", sub: "National infrastructure failure" }
      : { label: "TIMEOUT", colour: "#A3A3A3", sub: "Simulation time limit reached" }

  const last = history[history.length - 1] ?? {}
  const finalTurn = simState?.turn ?? 0
  const finalDisplaced = Object.values(last.total_displaced ?? {}).reduce((a, b) => a + b, 0)

  return (
    <AnimatePresence>
      {isTerminal ? (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.6 }} style={{ position: "fixed", inset: 0, zIndex: 100, background: "rgba(10,10,10,0.92)", backdropFilter: "blur(8px)", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: "0" }}>
          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.5 }} style={{ fontFamily: "monospace", fontSize: "11px", letterSpacing: "0.25em", textTransform: "uppercase", color: outcome.colour, marginBottom: "16px" }}>
            Simulation Complete
          </motion.div>

          <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.5, duration: 0.4 }} style={{ fontSize: "clamp(48px, 8vw, 96px)", fontWeight: 700, color: outcome.colour, letterSpacing: "-0.03em", lineHeight: 1, marginBottom: "12px" }}>
            {outcome.label}
          </motion.div>

          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.7 }} style={{ fontFamily: "monospace", fontSize: "12px", letterSpacing: "0.1em", textTransform: "uppercase", color: "#525252", marginBottom: "48px" }}>
            {outcome.sub}
          </motion.p>

          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.9 }} style={{ display: "flex", gap: "48px", marginBottom: "48px" }}>
            {[
              { label: "Turns elapsed", value: finalTurn },
              { label: "Total displaced", value: finalDisplaced.toLocaleString() },
              { label: "Nations", value: nations.length },
            ].map(({ label, value }) => (
              <div key={label} style={{ textAlign: "center" }}>
                <div style={{ fontFamily: "monospace", fontSize: "28px", fontWeight: 500, color: "#F5F5F5", letterSpacing: "-0.02em" }}>{value}</div>
                <div style={{ fontFamily: "monospace", fontSize: "9px", letterSpacing: "0.12em", textTransform: "uppercase", color: "#525252", marginTop: "4px" }}>{label}</div>
              </div>
            ))}
          </motion.div>

          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.1 }} style={{ display: "flex", gap: "16px", marginBottom: "48px" }}>
            {nations.map((nation) => {
              const cond = endConditions[nation] ?? "unknown"
              const colour = cond === "stabilised" ? "#22C55E" : cond === "collapsed" ? "#EF4444" : "#A3A3A3"
              return (
                <div key={nation} style={{ border: `1px solid ${colour}`, borderRadius: "4px", padding: "8px 20px", textAlign: "center" }}>
                  <div style={{ fontFamily: "monospace", fontSize: "10px", letterSpacing: "0.12em", textTransform: "uppercase", color: "#A3A3A3", marginBottom: "4px" }}>{nation}</div>
                  <div style={{ fontFamily: "monospace", fontSize: "11px", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: colour }}>{cond}</div>
                </div>
              )
            })}
          </motion.div>

          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.3 }} style={{ display: "flex", gap: "12px" }}>
            <button onClick={onRestart} style={{ padding: "10px 28px", background: "#212020", border: "1px solid #333333", borderRadius: "4px", color: "#F5F5F5", fontFamily: "monospace", fontSize: "11px", letterSpacing: "0.12em", textTransform: "uppercase", cursor: "pointer" }}>
              Restart
            </button>
            <button onClick={() => router.push("/setup")} style={{ padding: "10px 28px", background: "#3B82F6", border: "1px solid #3B82F6", borderRadius: "4px", color: "#ffffff", fontFamily: "monospace", fontSize: "11px", letterSpacing: "0.12em", textTransform: "uppercase", cursor: "pointer" }}>
              New Configuration
            </button>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  )
}
