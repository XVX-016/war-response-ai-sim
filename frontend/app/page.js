import dynamic from "next/dynamic"
import HeroText from "@/components/hero/HeroText"
import Navbar from "@/components/layout/Navbar"
import CapabilityCards from "@/components/home/CapabilityCards"
import HowItWorks from "@/components/home/HowItWorks"

const EarthScene = dynamic(() => import("@/components/hero/EarthScene"), { ssr: false })

export default function Home() {
  return (
    <main className="bg-[#0A0A0A] min-h-screen">
      <Navbar />
      <section className="relative h-screen overflow-hidden">
        <div className="absolute inset-0">
          <EarthScene />
        </div>
        <div className="absolute bottom-0 left-0 right-0 h-48 bg-gradient-to-t from-[#0A0A0A] to-transparent pointer-events-none" />
        <HeroText />
      </section>

      <section className="py-32 px-6 max-w-6xl mx-auto">
        <p className="text-xs font-mono tracking-[0.2em] uppercase text-[#525252] mb-4">System Capabilities</p>
        <h2 className="text-3xl font-bold text-[#F5F5F5] mb-16 tracking-tight">What ResilienceSim models</h2>
        <CapabilityCards />
      </section>

      <section className="py-32 px-6 max-w-6xl mx-auto border-t border-[#1F1F1F]">
        <p className="text-xs font-mono tracking-[0.2em] uppercase text-[#525252] mb-4">Pipeline</p>
        <h2 className="text-3xl font-bold text-[#F5F5F5] mb-16 tracking-tight">How it works</h2>
        <HowItWorks />
      </section>

      <footer className="border-t border-[#1F1F1F] py-12 px-6">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <span className="font-mono text-xs tracking-widest uppercase text-[#525252]">ResilienceSim</span>
          <span className="font-mono text-xs text-[#525252]">Civil Protection Infrastructure Simulator · 2026</span>
        </div>
      </footer>
    </main>
  )
}
