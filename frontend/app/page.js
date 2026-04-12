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

      <section className="py-16 md:py-32 px-4 md:px-6 max-w-6xl mx-auto">
        <p className="text-xs font-mono tracking-[0.2em] uppercase text-[#525252] mb-4">System Capabilities</p>
        <h2 className="text-2xl md:text-3xl font-bold text-[#F5F5F5] mb-8 md:mb-16 tracking-tight">What ResilienceSim models</h2>
        <CapabilityCards />
      </section>

      <section className="py-16 md:py-32 px-4 md:px-6 max-w-6xl mx-auto border-t border-[#1F1F1F]">
        <p className="text-xs font-mono tracking-[0.2em] uppercase text-[#525252] mb-4">Pipeline</p>
        <h2 className="text-2xl md:text-3xl font-bold text-[#F5F5F5] mb-8 md:mb-16 tracking-tight">How it works</h2>
        <HowItWorks />
      </section>

      <footer className="border-t border-[#1F1F1F] py-12 md:py-16 px-4 md:px-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 mb-12">
            <div>
              <span className="font-mono text-sm tracking-[0.15em] uppercase text-[#F5F5F5] block mb-3">Resilience-Sim</span>
              <p className="text-xs text-[#525252] leading-relaxed max-w-xs">
                AI-driven civil protection infrastructure simulator. Model cascading failures, test recovery strategies, and analyse humanitarian impact across configurable geopolitical scenarios.
              </p>
            </div>

            <div>
              <span className="font-mono text-[10px] tracking-[0.15em] uppercase text-[#525252] block mb-4">Navigation</span>
              <nav className="flex flex-col gap-2">
                <a href="/" className="text-xs text-[#A3A3A3] hover:text-[#F5F5F5] transition-colors">Home</a>
                <a href="/setup" className="text-xs text-[#A3A3A3] hover:text-[#F5F5F5] transition-colors">Setup</a>
                <a href="/sim" className="text-xs text-[#A3A3A3] hover:text-[#F5F5F5] transition-colors">Simulation</a>
                <a href="/vision" className="text-xs text-[#A3A3A3] hover:text-[#F5F5F5] transition-colors">Vision</a>
              </nav>
            </div>

            <div>
              <span className="font-mono text-[10px] tracking-[0.15em] uppercase text-[#525252] block mb-4">Links</span>
              <nav className="flex flex-col gap-2">
                <a href="https://github.com/XVX-016" target="_blank" rel="noopener noreferrer" className="text-xs text-[#A3A3A3] hover:text-[#F5F5F5] transition-colors">GitHub</a>
                <a href="https://tanmmay.me/" target="_blank" rel="noopener noreferrer" className="text-xs text-[#A3A3A3] hover:text-[#F5F5F5] transition-colors">Portfolio</a>
                <a href="https://www.linkedin.com/in/tanmmay-kanhaiya-9313492a3/" target="_blank" rel="noopener noreferrer" className="text-xs text-[#A3A3A3] hover:text-[#F5F5F5] transition-colors">LinkedIn</a>
              </nav>
            </div>
          </div>

          <div className="border-t border-[#1F1F1F] pt-6 flex flex-col md:flex-row justify-between items-center gap-2">
            <span className="font-mono text-[10px] tracking-[0.12em] uppercase text-[#333333]">Resilience-Sim · Civil Protection Infrastructure Simulator</span>
            <span className="font-mono text-[10px] text-[#333333]">© 2026 Tanmmay Kanhaiya</span>
          </div>
        </div>
      </footer>
    </main>
  )
}
