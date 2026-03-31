"use client"

import { useMemo, useState } from "react"
import { useSimStore } from "@/store/simStore"

function confidenceColour(value) {
  if (value >= 0.7) return "#22C55E"
  if (value >= 0.5) return "#F59E0B"
  return "#EF4444"
}

export default function DetectionResults({ result, previewUrl }) {
  const scenarioPath = useSimStore((s) => s.scenarioPath)
  const [nation, setNation] = useState("Auria")
  const suggestions = result?.suggestions || []
  const detections = result?.detections || []
  const imageSrc = result?.annotated_image_base64 ? `data:image/png;base64,${result.annotated_image_base64}` : previewUrl

  const rows = useMemo(() => {
    return [...suggestions].sort((a, b) => b.confidence - a.confidence)
  }, [suggestions])

  const uniqueTypes = new Set(rows.map((row) => row.asset_type)).size
  const meanConfidence = rows.length ? rows.reduce((sum, row) => sum + row.confidence, 0) / rows.length : 0

  if (!result.available) {
    return <div className="border border-[#333333] rounded p-4 text-[#A3A3A3]">Vision module unavailable. Install ultralytics or provide model weights.</div>
  }

  if (rows.length === 0 && detections.length === 0) {
    return <div className="border border-[#333333] rounded p-4 text-[#A3A3A3]">No civilian infrastructure detected.</div>
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_0.8fr] gap-6">
        <div className="border border-[#333333] rounded p-4 bg-[#212020]">
          {imageSrc ? <img src={imageSrc} alt="Detection preview" className="w-full rounded border border-[#333333]" /> : null}
          <p className="mt-3 text-sm text-[#A3A3A3]">Detected {detections.length} civilian infrastructure objects</p>
        </div>

        <div className="border border-[#333333] rounded p-4 bg-[#212020]">
          <div className="grid grid-cols-[1fr_auto_auto] gap-3 mb-3 text-[10px] uppercase tracking-[0.15em] font-mono text-[#525252]">
            <span>Asset Type</span>
            <span>Confidence</span>
            <span>Grid</span>
          </div>
          <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
            {rows.map((row, index) => (
              <div key={`${row.asset_type}-${row.row}-${row.col}-${index}`} className="grid grid-cols-[1fr_auto_auto] gap-3 items-center border-b border-[#1F1F1F] pb-2 text-sm text-[#A3A3A3]">
                <span>{row.asset_type.replaceAll("_", " ")}</span>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs" style={{ color: confidenceColour(row.confidence) }}>{Math.round(row.confidence * 100)}%</span>
                  <span className="block w-10 h-1 rounded bg-[#1A1A1A] overflow-hidden"><span className="block h-full" style={{ width: `${Math.round(row.confidence * 100)}%`, backgroundColor: confidenceColour(row.confidence) }} /></span>
                </div>
                <span className="font-mono text-xs text-[#525252]">r{row.row} c{row.col}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="border border-[#333333] rounded p-4 bg-[#212020]"><div className="text-[10px] uppercase tracking-[0.15em] font-mono text-[#525252] mb-2">Objects detected</div><div className="font-mono text-2xl text-[#F5F5F5]">{detections.length}</div></div>
        <div className="border border-[#333333] rounded p-4 bg-[#212020]"><div className="text-[10px] uppercase tracking-[0.15em] font-mono text-[#525252] mb-2">Asset types found</div><div className="font-mono text-2xl text-[#F5F5F5]">{uniqueTypes}</div></div>
        <div className="border border-[#333333] rounded p-4 bg-[#212020]"><div className="text-[10px] uppercase tracking-[0.15em] font-mono text-[#525252] mb-2">Mean confidence</div><div className="font-mono text-2xl text-[#F5F5F5]">{Math.round(meanConfidence * 100)}%</div></div>
      </div>

      <div className="border border-[#333333] rounded p-4 bg-[#212020] space-y-4">
        <div className="flex items-center gap-3 flex-wrap">
          <label className="text-sm text-[#A3A3A3]">Assign detections to nation:</label>
          <select value={nation} onChange={(e) => setNation(e.target.value)} className="bg-[#1A1A1A] border border-[#333333] rounded px-3 py-2 text-sm text-[#F5F5F5]">
            <option value="Auria">Auria</option>
            <option value="Boros">Boros</option>
          </select>
          <button className="px-4 py-2 rounded border border-[#3B82F6] bg-[#3B82F6] text-white text-xs font-mono uppercase tracking-[0.15em]" disabled={!scenarioPath}>
            Add to current scenario
          </button>
        </div>
        <button
          onClick={() => {
            const blob = new Blob([JSON.stringify({ nation, suggestions }, null, 2)], { type: "application/json" })
            const url = URL.createObjectURL(blob)
            const anchor = document.createElement("a")
            anchor.href = url
            anchor.download = "vision_patch.json"
            anchor.click()
            URL.revokeObjectURL(url)
          }}
          className="px-4 py-2 rounded border border-[#333333] text-[#A3A3A3] text-xs font-mono uppercase tracking-[0.15em]"
        >
          Download patch JSON
        </button>
      </div>
    </div>
  )
}
