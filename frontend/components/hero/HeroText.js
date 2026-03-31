"use client"

import Link from "next/link"
import { motion } from "framer-motion"

export default function HeroText() {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center z-10 pointer-events-none px-6">
      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="text-xs font-mono tracking-[0.2em] uppercase text-[#3B82F6] mb-4"
      >
        Civil Protection · Infrastructure Resilience · AI Simulation
      </motion.p>

      <motion.h1
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="text-6xl md:text-8xl font-bold text-center text-[#F5F5F5] leading-tight tracking-tight mb-4"
      >
        Infrastructure
        <br />
        <span className="text-[#3B82F6]">Resilience</span>
      </motion.h1>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.7 }}
        className="text-sm md:text-base font-mono tracking-widest uppercase text-[#525252] mb-12 text-center"
      >
        Multi-Agent Crisis Simulation · Cascade Failure Modelling · AI Recovery
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9 }}
        className="flex gap-4 pointer-events-auto"
      >
        <Link href="/setup">
          <button className="px-8 py-3 bg-[#3B82F6] text-white text-sm font-mono tracking-widest uppercase border border-[#3B82F6] rounded hover:bg-[#1D4ED8] transition-colors">
            Enter Simulator
          </button>
        </Link>
        <a
          href="https://github.com/YOUR_USERNAME/war-response-ai-sim"
          target="_blank"
          rel="noreferrer"
          className="px-8 py-3 bg-transparent text-[#A3A3A3] text-sm font-mono tracking-widest uppercase border border-[#333333] rounded hover:border-[#A3A3A3] hover:text-[#F5F5F5] transition-colors pointer-events-auto"
        >
          GitHub
        </a>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.4 }}
        className="absolute bottom-8 flex flex-col items-center gap-2"
      >
        <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[#525252]">Scroll</span>
        <div className="w-px h-8 bg-gradient-to-b from-[#333333] to-transparent" />
      </motion.div>
    </div>
  )
}
