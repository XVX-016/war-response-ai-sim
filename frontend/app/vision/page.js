"use client"

import Navbar from "@/components/layout/Navbar"
import VisionUploader from "@/components/vision/VisionUploader"

export default function VisionPage() {
  return (
    <main className="min-h-screen bg-[#0A0A0A] pt-20 pb-16 px-4 md:px-6">
      <Navbar />
      <div className="max-w-7xl mx-auto space-y-8">
        <div>
          <p className="text-xs font-mono tracking-[0.2em] uppercase text-[#525252] mb-2">Computer Vision</p>
          <h1 className="text-2xl md:text-4xl font-bold text-[#F5F5F5] tracking-tight mb-3">Infrastructure Vision</h1>
          <p className="text-sm text-[#525252] max-w-3xl">
            Upload aerial or satellite imagery to detect civilian infrastructure, estimate likely asset types, and export a JSON patch for scenario seeding.
          </p>
          <div className="mt-4 flex items-center gap-2 rounded border border-[#2D1A00] bg-[#1A1400] px-4 py-3 max-w-md">
            <span className="text-[#FCD34D] text-sm">⚠</span>
            <span className="font-mono text-[11px] tracking-[0.06em] text-[#FCD34D]">Under construction — this module is still in development.</span>
          </div>
        </div>
        <VisionUploader />
      </div>
    </main>
  )
}
