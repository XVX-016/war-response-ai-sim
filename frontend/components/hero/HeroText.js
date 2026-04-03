"use client"

import Link from "next/link"
import { motion } from "framer-motion"

export default function HeroText() {
  return (
    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center px-6 pointer-events-none">
      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="mb-4 text-xs font-mono uppercase tracking-[0.2em] text-[#3B82F6]"
      >
        Civil Protection · Infrastructure Resilience · AI Simulation
      </motion.p>

      <motion.h1
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="mb-4 text-center text-6xl font-bold leading-tight tracking-tight text-[#F5F5F5] md:text-8xl"
      >
        Infrastructure
        <br />
        <span className="text-[#3B82F6]">Resilience</span>
      </motion.h1>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.7 }}
        className="mb-12 text-center text-sm font-mono uppercase tracking-widest text-[#525252] md:text-base"
      >
        Multi-Agent Crisis Simulation · Cascade Failure Modelling · AI Recovery
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9 }}
        className="pointer-events-auto flex gap-4"
      >
        <Link href="/setup">
          <button className="rounded border border-[#3B82F6] bg-[#3B82F6] px-8 py-3 text-sm font-mono uppercase tracking-widest text-white transition-colors hover:bg-[#1D4ED8]">
            Enter Simulator
          </button>
        </Link>
        <a
          href="https://github.com/YOUR_USERNAME/war-response-ai-sim"
          target="_blank"
          rel="noreferrer"
          className="pointer-events-auto rounded border border-[#333333] bg-transparent px-8 py-3 text-sm font-mono uppercase tracking-widest text-[#A3A3A3] transition-colors hover:border-[#A3A3A3] hover:text-[#F5F5F5]"
        >
          GitHub
        </a>
      </motion.div>
    </div>
  )
}
