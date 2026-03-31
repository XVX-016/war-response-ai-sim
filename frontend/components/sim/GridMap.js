"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { useSimStore } from "@/store/simStore"

const ASSET_LETTER = {
  power_plant: "P",
  water_treatment: "W",
  hospital: "H",
  telecom_tower: "T",
  transport_hub: "X",
  fuel_depot: "F",
  shelter: "S",
  command_center: "C",
}

const STATUS_FILL = {
  healthy: "#22C55E",
  degraded: "#F59E0B",
  critical: "#EF4444",
  destroyed: "#525252",
}

const NATION_BORDER = {
  Auria: "#3B82F6",
  Boros: "#F59E0B",
}

const CELL_SIZE = 32
const GRID_SIZE = 20
const CANVAS_SIZE = CELL_SIZE * GRID_SIZE

function getAssetStatus(asset) {
  if (asset.is_destroyed || asset.health <= 0) return "destroyed"
  const fraction = asset.max_health > 0 ? asset.health / asset.max_health : 0
  if (fraction < 0.35) return "critical"
  if (fraction < 0.7) return "degraded"
  return "healthy"
}

export default function GridMap({ simState, nationFilter = "All" }) {
  const canvasRef = useRef(null)
  const flashRef = useRef(new Map())
  const previousStatusesRef = useRef(new Map())
  const [tooltip, setTooltip] = useState(null)
  const setSelectedAsset = useSimStore((s) => s.setSelectedAsset)

  const assetGrid = useMemo(() => {
    const map = new Map()
    const assets = simState?.assets || []
    assets.forEach((asset) => {
      map.set(`${asset.row},${asset.col}`, asset)
    })
    return map
  }, [simState])

  useEffect(() => {
    const nextStatuses = new Map()
    ;(simState?.assets || []).forEach((asset) => {
      const next = getAssetStatus(asset)
      const prev = previousStatusesRef.current.get(asset.id)
      if (prev && prev !== next) {
        flashRef.current.set(asset.id, 3)
      }
      nextStatuses.set(asset.id, next)
    })
    previousStatusesRef.current = nextStatuses
  }, [simState])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    ctx.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE)

    for (let row = 0; row < GRID_SIZE; row += 1) {
      for (let col = 0; col < GRID_SIZE; col += 1) {
        const x = col * CELL_SIZE
        const y = row * CELL_SIZE
        const asset = assetGrid.get(`${row},${col}`)
        const nationDimmed = asset && nationFilter !== "All" && asset.nation !== nationFilter

        ctx.fillStyle = "#1A1A1A"
        ctx.fillRect(x, y, CELL_SIZE, CELL_SIZE)
        ctx.strokeStyle = "#2D2C2C"
        ctx.strokeRect(x, y, CELL_SIZE, CELL_SIZE)

        if (!asset) continue

        const status = getAssetStatus(asset)
        const flashFrames = flashRef.current.get(asset.id) || 0
        ctx.globalAlpha = nationDimmed ? 0.2 : 1
        ctx.fillStyle = flashFrames > 0 ? "#F5F5F5" : STATUS_FILL[status]
        ctx.fillRect(x + 1, y + 1, CELL_SIZE - 2, CELL_SIZE - 2)
        ctx.globalAlpha = nationDimmed ? 0.3 : 1
        ctx.strokeStyle = NATION_BORDER[asset.nation] || "#333333"
        ctx.lineWidth = 2
        ctx.strokeRect(x + 3, y + 3, CELL_SIZE - 6, CELL_SIZE - 6)

        if (asset.is_reinforced) {
          ctx.strokeStyle = "#FFFFFF"
          ctx.lineWidth = 2
          ctx.strokeRect(x + 7, y + 7, CELL_SIZE - 14, CELL_SIZE - 14)
        }

        ctx.globalAlpha = nationDimmed ? 0.4 : 1
        ctx.fillStyle = "#F5F5F5"
        ctx.font = "13px JetBrains Mono, monospace"
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        ctx.fillText(status === "destroyed" ? "×" : ASSET_LETTER[asset.asset_type] || "?", x + CELL_SIZE / 2, y + CELL_SIZE / 2 + 1)
        ctx.globalAlpha = 1

        if (flashFrames > 0) {
          flashRef.current.set(asset.id, flashFrames - 1)
        }
      }
    }

    ctx.strokeStyle = "#A3A3A3"
    ctx.setLineDash([6, 4])
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(0, CELL_SIZE * 10)
    ctx.lineTo(CANVAS_SIZE, CELL_SIZE * 10)
    ctx.stroke()
    ctx.setLineDash([])
  }, [assetGrid, nationFilter, simState])

  const handlePointer = (event) => {
    const rect = canvasRef.current.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top
    const row = Math.max(0, Math.min(GRID_SIZE - 1, Math.floor(y / CELL_SIZE)))
    const col = Math.max(0, Math.min(GRID_SIZE - 1, Math.floor(x / CELL_SIZE)))
    const asset = assetGrid.get(`${row},${col}`)
    if (!asset) {
      setTooltip(null)
      return
    }
    setTooltip({
      x: x + 16,
      y: y + 16,
      asset,
      status: getAssetStatus(asset),
    })
  }

  return (
    <div className="relative border border-[#333333] rounded p-4 bg-[#212020] w-fit mx-auto">
      <canvas
        ref={canvasRef}
        width={CANVAS_SIZE}
        height={CANVAS_SIZE}
        className="max-w-full h-auto cursor-crosshair"
        onMouseMove={handlePointer}
        onMouseLeave={() => setTooltip(null)}
        onClick={(event) => {
          const rect = canvasRef.current.getBoundingClientRect()
          const row = Math.floor((event.clientY - rect.top) / CELL_SIZE)
          const col = Math.floor((event.clientX - rect.left) / CELL_SIZE)
          const asset = assetGrid.get(`${row},${col}`)
          if (asset) setSelectedAsset(asset.id)
        }}
      />
      {tooltip ? (
        <div
          className="absolute pointer-events-none border border-[#333333] rounded bg-[#0A0A0A] px-3 py-2 text-xs min-w-[180px]"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          <div className="text-[#F5F5F5] font-semibold mb-1">{tooltip.asset.name}</div>
          <div className="font-mono text-[#A3A3A3] mb-1">{Math.round(tooltip.asset.health)}/{Math.round(tooltip.asset.max_health)} HP</div>
          <div className="text-[#A3A3A3] capitalize">{tooltip.status}</div>
          <div className="text-[#525252]">{tooltip.asset.nation}</div>
        </div>
      ) : null}
    </div>
  )
}
