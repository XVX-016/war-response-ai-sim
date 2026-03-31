"use client"

import { useState } from "react"
import { CloudUpload } from "lucide-react"
import { api } from "@/lib/api"
import DetectionResults from "@/components/vision/DetectionResults"

export default function VisionUploader() {
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [result, setResult] = useState(null)
  const [previewUrl, setPreviewUrl] = useState("")

  const processFile = async (file) => {
    if (!file) return
    setLoading(true)
    setError("")
    const localPreview = URL.createObjectURL(file)
    setPreviewUrl(localPreview)
    try {
      const response = await api.detectVision(file)
      setResult(response)
    } catch (err) {
      setError(err.message || "Vision detection failed")
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <label
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          processFile(e.dataTransfer.files?.[0])
        }}
        className={`block border rounded p-12 text-center transition-colors ${dragging ? "border-[#3B82F6]" : "border-[#333333]"} bg-[#0A0A0A] cursor-pointer`}
      >
        <CloudUpload className="mx-auto mb-4 text-[#A3A3A3]" size={28} />
        <div className="text-[#F5F5F5] mb-2">Drag aerial image here</div>
        <div className="text-[#525252] font-mono text-xs uppercase tracking-[0.15em]">JPG · PNG · TIF up to 200MB</div>
        <input type="file" accept=".jpg,.jpeg,.png,.tif,.tiff" className="hidden" onChange={(e) => processFile(e.target.files?.[0])} />
      </label>

      {loading ? <div className="text-[#A3A3A3] font-mono text-sm">Running infrastructure detection…</div> : null}
      {error ? <div className="border border-[#EF4444] rounded p-3 text-[#EF4444] font-mono text-sm">{error}</div> : null}
      {result ? <DetectionResults result={result} previewUrl={previewUrl} /> : null}
    </div>
  )
}
