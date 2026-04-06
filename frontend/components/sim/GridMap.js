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

const STATUS_ORDER = { healthy: 0, degraded: 1, critical: 2, destroyed: 3 }
const NATION_BORDER = { Auria: "#3B82F6", Boros: "#F59E0B" }
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

function hexToRgb(hex) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return { r, g, b }
}

function lerpColour(a, b, t) {
  return {
    r: Math.round(a.r + (b.r - a.r) * t),
    g: Math.round(a.g + (b.g - a.g) * t),
    b: Math.round(a.b + (b.b - a.b) * t),
  }
}

function rgbToFill({ r, g, b }) {
  return `rgb(${r},${g},${b})`
}

function easeOut(t) {
  return 1 - Math.pow(1 - t, 3)
}

export default function GridMap({ simState, nationFilter = "All", onAssetClick }) {
  const canvasRef = useRef(null)
  const previousStatusesRef = useRef(new Map())
  const prevColoursRef = useRef({})
  const animProgressRef = useRef({})
  const flashRef = useRef({})
  const animFrameRef = useRef(null)
  const lastFrameTimeRef = useRef(null)
  const [tooltip, setTooltip] = useState(null)
  const [renderTick, setRenderTick] = useState(0)
  const selectedAssetId = useSimStore((s) => s.selectedAsset)
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
      const nextStatus = getAssetStatus(asset)
      const targetColour = hexToRgb(STATUS_FILL[nextStatus])
      const prevStatus = previousStatusesRef.current.get(asset.id)
      const oldColour = prevStatus ? prevColoursRef.current[asset.id] ?? hexToRgb(STATUS_FILL[prevStatus]) : targetColour

      if (prevStatus && prevStatus !== nextStatus) {
        animProgressRef.current[asset.id] = 0
        prevColoursRef.current[asset.id] = oldColour
        if (STATUS_ORDER[nextStatus] > STATUS_ORDER[prevStatus]) {
          flashRef.current[asset.id] = 3
        }
      } else {
        animProgressRef.current[asset.id] = 1
        prevColoursRef.current[asset.id] = targetColour
      }

      nextStatuses.set(asset.id, nextStatus)
    })
    previousStatusesRef.current = nextStatuses
  }, [simState])

  useEffect(() => {
    const tick = (time) => {
      if (lastFrameTimeRef.current == null) lastFrameTimeRef.current = time
      const delta = time - lastFrameTimeRef.current
      lastFrameTimeRef.current = time
      let hasActive = false

      Object.keys(animProgressRef.current).forEach((assetId) => {
        const progress = animProgressRef.current[assetId] ?? 1
        if (progress < 1) {
          animProgressRef.current[assetId] = Math.min(1, progress + delta / 400)
          if (animProgressRef.current[assetId] < 1) hasActive = true
        }
      })

      Object.keys(flashRef.current).forEach((assetId) => {
        if (flashRef.current[assetId] > 0) {
          flashRef.current[assetId] -= 1
          hasActive = true
        } else {
          delete flashRef.current[assetId]
        }
      })

      setRenderTick((value) => value + 1)

      if (hasActive) {
        animFrameRef.current = window.requestAnimationFrame(tick)
      } else {
        animFrameRef.current = null
        lastFrameTimeRef.current = null
      }
    }

    const shouldAnimate = Object.values(animProgressRef.current).some((value) => value < 1) || Object.keys(flashRef.current).length > 0
    if (shouldAnimate && !animFrameRef.current) {
      animFrameRef.current = window.requestAnimationFrame(tick)
    }

    return () => {
      if (animFrameRef.current) {
        window.cancelAnimationFrame(animFrameRef.current)
        animFrameRef.current = null
      }
      lastFrameTimeRef.current = null
    }
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
        ctx.lineWidth = 1
        ctx.strokeRect(x, y, CELL_SIZE, CELL_SIZE)

        if (!asset) continue

        const status = getAssetStatus(asset)
        const targetColour = hexToRgb(STATUS_FILL[status])
        const prevColour = prevColoursRef.current[asset.id] ?? targetColour
        const progress = animProgressRef.current[asset.id] ?? 1
        const fillColour = flashRef.current[asset.id] > 0 ? "rgba(255, 255, 255, 0.85)" : rgbToFill(lerpColour(prevColour, targetColour, easeOut(progress)))

        ctx.globalAlpha = nationDimmed ? 0.2 : 1
        ctx.fillStyle = fillColour
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

        if (selectedAssetId === asset.id) {
          ctx.strokeStyle = "#FFFFFF"
          ctx.lineWidth = 2
          ctx.strokeRect(x + 5, y + 5, CELL_SIZE - 10, CELL_SIZE - 10)
        }

        ctx.globalAlpha = nationDimmed ? 0.4 : 1
        ctx.fillStyle = "#F5F5F5"
        ctx.font = "13px Space Mono, monospace"
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        ctx.fillText(status === "destroyed" ? "×" : ASSET_LETTER[asset.asset_type] || "?", x + CELL_SIZE / 2, y + CELL_SIZE / 2 + 1)
        ctx.globalAlpha = 1
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
  }, [assetGrid, nationFilter, renderTick, selectedAssetId, simState])

  const getCellFromEvent = (event) => {
    const rect = canvasRef.current.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top
    const row = Math.max(0, Math.min(GRID_SIZE - 1, Math.floor(y / CELL_SIZE)))
    const col = Math.max(0, Math.min(GRID_SIZE - 1, Math.floor(x / CELL_SIZE)))
    return { row, col, x, y }
  }

  const handlePointer = (event) => {
    const { row, col, x, y } = getCellFromEvent(event)
    const asset = assetGrid.get(`${row},${col}`)
    if (!asset) {
      setTooltip(null)
      return
    }
    setTooltip({ x: x + 16, y: y + 16, asset, status: getAssetStatus(asset) })
  }

  return (
    <div className="relative mx-auto w-fit rounded border border-[#333333] bg-[#212020] p-4">
      <canvas
        ref={canvasRef}
        width={CANVAS_SIZE}
        height={CANVAS_SIZE}
        className="h-auto max-w-full cursor-crosshair"
        onMouseMove={handlePointer}
        onMouseLeave={() => setTooltip(null)}
        onClick={(event) => {
          const { row, col } = getCellFromEvent(event)
          const asset = assetGrid.get(`${row},${col}`)
          const nextId = asset ? asset.id : null
          setSelectedAsset(nextId)
          onAssetClick?.(nextId)
        }}
      />
      <div style={{ display: "flex", gap: "16px", padding: "10px 0", alignItems: "center" }}>
        {[
          { colour: "#22C55E", label: "Healthy" },
          { colour: "#F59E0B", label: "Degraded" },
          { colour: "#EF4444", label: "Critical" },
          { colour: "#525252", label: "Destroyed" },
        ].map(({ colour, label }) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <div style={{ width: "8px", height: "8px", borderRadius: "2px", background: colour }} />
            <span style={{ fontFamily: "Space Mono, monospace", fontSize: "10px", letterSpacing: "0.08em", textTransform: "uppercase", color: "#525252" }}>{label}</span>
          </div>
        ))}
      </div>
      {tooltip ? (
        <div className="pointer-events-none absolute min-w-[180px] rounded border border-[#333333] bg-[#0A0A0A] px-3 py-2 text-xs" style={{ left: tooltip.x, top: tooltip.y }}>
          <div className="mb-1 font-semibold text-[#F5F5F5]">{tooltip.asset.name}</div>
          <div className="mb-1 font-mono text-[#A3A3A3]">{Math.round(tooltip.asset.health)}/{Math.round(tooltip.asset.max_health)} HP</div>
          <div className="capitalize text-[#A3A3A3]">{tooltip.status}</div>
          <div className="text-[#525252]">{tooltip.asset.nation}</div>
        </div>
      ) : null}
    </div>
  )
}
