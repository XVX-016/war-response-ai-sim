"use client"

import { useEffect, useRef, useState } from "react"
import { countryToProfile, loadCountryCache } from "@/lib/countries"

export default function CountrySearch({ accentColour, onSelect }) {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState([])
  const [cache, setCache] = useState({})
  const [open, setOpen] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const inputRef = useRef(null)

  useEffect(() => {
    loadCountryCache().then(setCache)
  }, [])

  useEffect(() => {
    if (!query.trim()) {
      setResults([])
      return
    }
    const needle = query.toLowerCase()
    const matches = Object.entries(cache)
      .filter(([name]) => name.toLowerCase().includes(needle))
      .slice(0, 8)
      .map(([name, data]) => ({ name, data }))
    setResults(matches)
    setOpen(matches.length > 0)
  }, [cache, query])

  function handleSelect(countryName, countryData) {
    const profile = countryToProfile(countryName, countryData)
    onSelect(profile, countryName)
    setQuery(countryName)
    setOpen(false)
  }

  async function handleRefresh() {
    setRefreshing(true)
    try {
      await fetch("/api/countries/refresh", { method: "POST" })
      const freshCache = await loadCountryCache()
      setCache(freshCache)
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <div style={{ position: "relative", marginBottom: "16px" }}>
      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
        <input
          ref={inputRef}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onFocus={() => query && setOpen(true)}
          placeholder="Search real country... or use fictional"
          style={{
            flex: 1,
            background: "#1A1A1A",
            border: `1px solid ${open ? accentColour : "#333333"}`,
            borderRadius: "4px",
            padding: "8px 12px",
            fontFamily: "Space Mono, monospace",
            fontSize: "12px",
            color: "#F5F5F5",
            outline: "none",
            transition: "border-color 150ms ease",
          }}
        />
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          title="Refresh from World Bank API"
          style={{
            padding: "8px 10px",
            background: "#212020",
            border: "1px solid #333333",
            borderRadius: "4px",
            color: "#525252",
            cursor: "pointer",
            fontSize: "11px",
            fontFamily: "Space Mono, monospace",
            whiteSpace: "nowrap",
          }}
        >
          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {open ? (
        <div
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            zIndex: 50,
            background: "#212020",
            border: "1px solid #333333",
            borderRadius: "4px",
            marginTop: "4px",
            maxHeight: "240px",
            overflowY: "auto",
          }}
        >
          {results.map(({ name, data }) => (
            <button
              key={name}
              onClick={() => handleSelect(name, data)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                width: "100%",
                padding: "10px 12px",
                background: "transparent",
                border: "none",
                borderBottom: "1px solid #1F1F1F",
                cursor: "pointer",
                textAlign: "left",
              }}
            >
              <span style={{ fontSize: "16px" }}>{data.flag}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: "Space Mono, monospace", fontSize: "12px", color: "#F5F5F5" }}>{name}</div>
                <div style={{ fontFamily: "Space Mono, monospace", fontSize: "10px", color: "#525252" }}>
                  {data.region} · GDP {data.gdp_index} · Military {data.military_strength}
                </div>
              </div>
              <div style={{ display: "flex", gap: "2px", alignItems: "center" }}>
                {[data.gdp_index, data.military_strength, data.resource_richness, data.alliance_strength].map((value, index) => (
                  <div
                    key={index}
                    style={{
                      width: "3px",
                      height: `${Math.round(value * 16) + 4}px`,
                      background: accentColour,
                      opacity: 0.6,
                      borderRadius: "1px",
                    }}
                  />
                ))}
              </div>
            </button>
          ))}
        </div>
      ) : null}

      <div
        style={{
          fontFamily: "Space Mono, monospace",
          fontSize: "9px",
          color: "#333333",
          marginTop: "4px",
          letterSpacing: "0.05em",
        }}
      >
        {Object.keys(cache).length} countries loaded · World Bank data
      </div>
    </div>
  )
}
