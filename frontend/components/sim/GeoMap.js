"use client"

import { useEffect, useRef, useState } from "react"
import { useSimStore } from "@/store/simStore"
import GridMap from "@/components/sim/GridMap"

const ABBREV = {
  power_plant: "P",
  water_treatment: "W",
  hospital: "H",
  telecom_tower: "T",
  transport_hub: "X",
  fuel_depot: "F",
  shelter: "S",
  command_center: "C",
}

const STATUS_COLOUR = {
  healthy: "#22C55E",
  degraded: "#F59E0B",
  critical: "#EF4444",
  destroyed: "#525252",
}

const NATION_COLOUR = (nations, nation) => (nation === nations[0] ? "#3B82F6" : "#F59E0B")

export default function GeoMap({ onAssetClick, proposedActions, nationFilter }) {
  const mapRef = useRef(null)
  const leafletRef = useRef(null)
  const markersRef = useRef({})
  const simState = useSimStore((s) => s.simState)
  const geoNations = useSimStore((s) => s.geoNations)
  const [leafletFailed, setLeafletFailed] = useState(false)
  const hasGeo = simState?.metadata?.["_has_geo"] === true || simState?.metadata?.["_has_geo"]?.enabled === true
  const nations = simState?.nations ?? []

  const displayNationName = (nation) => geoNations?.[nation] || nation

  const getMapConfig = () => {
    if (!hasGeo || !simState?.metadata) return { center: [20, 0], zoom: 2 }
    const centers = nations.map((nation) => simState.metadata[nation]?.map_center).filter(Boolean)
    if (centers.length === 0) return { center: [20, 0], zoom: 2 }
    const lat = centers.reduce((sum, c) => sum + c[0], 0) / centers.length
    const lon = centers.reduce((sum, c) => sum + c[1], 0) / centers.length
    const zoom = centers.length === 2 ? 3 : (simState.metadata[nations[0]]?.map_zoom ?? 5)
    return { center: [lat, lon], zoom }
  }

  useEffect(() => {
    if (!hasGeo) return undefined
    const timeout = window.setTimeout(() => {
      if (!leafletRef.current) setLeafletFailed(true)
    }, 3000)
    return () => window.clearTimeout(timeout)
  }, [hasGeo])

  useEffect(() => {
    if (typeof window === "undefined" || !mapRef.current || leafletFailed || !hasGeo) return undefined
    if (leafletRef.current) return undefined

    let cancelled = false

    import("leaflet")
      .then((L) => {
        if (cancelled || !mapRef.current) return

        if (mapRef.current._leaflet_id) {
          mapRef.current._leaflet_id = undefined
        }

        delete L.Icon.Default.prototype._getIconUrl
        L.Icon.Default.mergeOptions({
          iconRetinaUrl: "/leaflet/marker-icon-2x.png",
          iconUrl: "/leaflet/marker-icon.png",
          shadowUrl: "/leaflet/marker-shadow.png",
        })

        const { center, zoom } = getMapConfig()
        const map = L.map(mapRef.current, {
          center,
          zoom,
          zoomControl: true,
          attributionControl: false,
        })

        L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
          maxZoom: 19,
          subdomains: "abcd",
        }).addTo(map)

        leafletRef.current = { map, L }
        renderMarkers(map, L)
      })
      .catch(() => {
        setLeafletFailed(true)
      })

    return () => {
      cancelled = true
      if (leafletRef.current?.map) {
        leafletRef.current.map.remove()
        leafletRef.current = null
      }
    }
  }, [hasGeo, leafletFailed])

  useEffect(() => {
    if (!leafletRef.current || leafletFailed) return
    const { map, L } = leafletRef.current
    renderMarkers(map, L)
  }, [simState, proposedActions, nationFilter, leafletFailed])

  function renderMarkers(map, L) {
    if (!simState?.assets) return

    Object.values(markersRef.current).forEach((marker) => {
      if (marker) map.removeLayer(marker)
    })
    markersRef.current = {}

    const assets = simState.assets.filter((asset) => {
      if (asset.lat == null || asset.lon == null) return false
      if (nationFilter && nationFilter !== "All" && asset.nation !== nationFilter) return false
      return true
    })

    assets.forEach((asset) => {
      const health = asset.max_health > 0 ? asset.health / asset.max_health : 0
      const status = asset.is_destroyed ? "destroyed" : health < 0.25 ? "critical" : health < 0.5 ? "degraded" : "healthy"
      const colour = STATUS_COLOUR[status]
      const letter = ABBREV[asset.asset_type] || "?"
      const isProp = proposedActions?.some((action) => action.target_asset_id === asset.id)

      const icon = L.divIcon({
        className: "",
        html: `
          <div style="
            width: 32px; height: 32px;
            background: ${colour};
            border: 2px solid ${NATION_COLOUR(nations, asset.nation)};
            border-radius: 4px;
            display: flex; align-items: center; justify-content: center;
            font-family: 'DM Mono', monospace;
            font-size: 13px; font-weight: 700;
            color: white;
            cursor: pointer;
            ${isProp ? "box-shadow: 0 0 0 3px #F59E0B;" : ""}
            ${asset.is_reinforced ? "outline: 2px solid white; outline-offset: 1px;" : ""}
            opacity: ${status === "destroyed" ? 0.5 : 1};
          ">
            ${status === "destroyed" ? "x" : letter}
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      })

      const tooltipHtml = `
        <div style="
          background: #212020; border: 1px solid #333333;
          border-radius: 4px; padding: 8px 10px;
          font-family: 'DM Sans', sans-serif; font-size: 11px;
          color: #F5F5F5; min-width: 160px;
        ">
          <div style="font-weight:700; margin-bottom:4px;">${asset.geo_name || asset.name || asset.id}</div>
          <div style="color:#A3A3A3; font-size:10px; margin-bottom:2px;">
            ${asset.asset_type.replace(/_/g, " ").toUpperCase()}
          </div>
          <div style="color:${colour}; font-size:10px; font-family:'DM Mono', monospace;">
            ${Math.round(asset.health)}/${asset.max_health} HP - ${status.toUpperCase()}
          </div>
          <div style="color:#525252; font-size:9px; margin-top:4px;">${displayNationName(asset.nation)}</div>
        </div>
      `

      const marker = L.marker([asset.lat, asset.lon], { icon })
        .addTo(map)
        .bindTooltip(tooltipHtml, {
          className: "leaflet-custom-tooltip",
          permanent: false,
          direction: "top",
          offset: [0, -16],
        })
        .on("click", () => onAssetClick?.(asset.id))

      markersRef.current[asset.id] = marker
    })

    simState.zones?.forEach((zone) => {
      if (zone.lat == null || zone.lon == null) return
      if (nationFilter && nationFilter !== "All" && zone.nation !== nationFilter) return

      const displacedFraction = zone.population > 0 ? zone.displaced / zone.population : 0
      const colour = displacedFraction > 0.1 ? "#EF4444" : "#525252"

      const zoneIcon = L.divIcon({
        className: "",
        html: `
          <div style="
            width: 8px; height: 8px;
            background: ${colour};
            border-radius: 50%;
            border: 1px solid #333333;
            opacity: 0.7;
          "></div>
        `,
        iconSize: [8, 8],
        iconAnchor: [4, 4],
      })

      const marker = L.marker([zone.lat, zone.lon], { icon: zoneIcon })
        .addTo(map)
        .bindTooltip(
          `
          <div style="background:#212020; border:1px solid #333333;
                      border-radius:4px; padding:6px 8px;
                      font-family:'DM Sans',sans-serif; font-size:10px; color:#F5F5F5;">
            <div>${zone.name || zone.id}</div>
            <div style="color:#A3A3A3;">Pop: ${(zone.population / 1000).toFixed(0)}k</div>
            <div style="color:#525252;">${displayNationName(zone.nation)}</div>
            ${zone.displaced > 0 ? `<div style="color:#EF4444;">Displaced: ${zone.displaced.toLocaleString()}</div>` : ""}
          </div>
        `,
          { className: "", direction: "top" }
        )

      markersRef.current[`zone_${zone.id}`] = marker
    })
  }

  useEffect(() => {
    const style = document.createElement("style")
    style.textContent = `
      .leaflet-custom-tooltip {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
      }
      .leaflet-custom-tooltip::before { display: none !important; }
      .leaflet-container {
        background: #0A0A0A;
        font-family: "DM Sans", system-ui, sans-serif;
      }
    `
    document.head.appendChild(style)
    return () => document.head.removeChild(style)
  }, [])

  if (!hasGeo) return null
  if (leafletFailed) {
    return <GridMap simState={simState} nationFilter={nationFilter} onAssetClick={onAssetClick} />
  }

  return (
    <div style={{ position: "relative" }}>
      <div
        ref={mapRef}
        style={{
          width: "100%",
          height: "480px",
          borderRadius: "4px",
          border: "1px solid #333333",
          background: "#0A0A0A",
        }}
      />
      <div style={{ display: "flex", gap: "16px", padding: "8px 0", alignItems: "center", flexWrap: "wrap" }}>
        {[
          { colour: "#22C55E", label: "Healthy" },
          { colour: "#F59E0B", label: "Degraded" },
          { colour: "#EF4444", label: "Critical" },
          { colour: "#525252", label: "Destroyed" },
        ].map(({ colour, label }) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <div style={{ width: "8px", height: "8px", borderRadius: "2px", background: colour }} />
            <span style={{ fontFamily: "DM Mono, monospace", fontSize: "10px", letterSpacing: "0.08em", textTransform: "uppercase", color: "#525252" }}>
              {label}
            </span>
          </div>
        ))}
        <span style={{ fontFamily: "DM Mono, monospace", fontSize: "9px", color: "#333333", marginLeft: "auto" }}>
          P=Power W=Water H=Hospital T=Telecom X=Transport F=Fuel S=Shelter C=Command
        </span>
      </div>
    </div>
  )
}
