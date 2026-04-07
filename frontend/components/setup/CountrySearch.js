"use client"

import { useEffect, useRef, useState } from "react"
import { countryToProfile, loadCountryCache } from "@/lib/countries"
import { useSimStore } from "@/store/simStore"

export default function CountrySearch({ accentColour, onSelect }) {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState([])
  const [cache, setCache] = useState({})
  const [selectedCountry, setSelectedCountry] = useState("")
  const [open, setOpen] = useState(false)
  const [mode, setMode] = useState("select")
  const [refreshing, setRefreshing] = useState(false)
  const inputRef = useRef(null)
  const cachedData = useSimStore((s) => s.countryCache)
  const setCountryCache = useSimStore((s) => s.setCountryCache)

  useEffect(() => {
    if (Object.keys(cachedData).length > 0) {
      setCache(cachedData)
      return
    }
    loadCountryCache().then((data) => {
      setCache(data)
      setCountryCache(data)
    })
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
    setSelectedCountry(countryName)
    setOpen(false)
    setResults([])
    inputRef.current?.blur()
  }

  async function handleRefresh() {
    setRefreshing(true)
    try {
      await fetch("/api/countries/refresh", { method: "POST" })
      const freshCache = await loadCountryCache()
      setCache(freshCache)
      setCountryCache(freshCache)
    } finally {
      setRefreshing(false)
    }
  }

  const regions = {}
  Object.entries(cache).forEach(([name, data]) => {
    const region = data.region || "Other"
    if (!regions[region]) regions[region] = []
    regions[region].push([name, data])
  })

  return (
    <div style={{ position: "relative", marginBottom: "16px", zIndex: 40 }}>
      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
        {mode === "select" ? (
          <select
            value={selectedCountry}
            onChange={(event) => {
              const name = event.target.value
              if (name && cache[name]) {
                handleSelect(name, cache[name])
              }
            }}
            style={{
              flex: 1,
              width: "100%",
              background: "#1A1A1A",
              border: "1px solid #333333",
              borderRadius: "4px",
              padding: "8px 12px",
              fontFamily: "DM Mono, monospace",
              fontSize: "12px",
              color: "#F5F5F5",
              cursor: "pointer",
              appearance: "none",
              backgroundImage:
                "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath fill='%23999999' d='M0 0l5 6 5-6z'/%3E%3C/svg%3E\")",
              backgroundRepeat: "no-repeat",
              backgroundPosition: "right 10px center",
              paddingRight: "28px",
            }}
          >
            <option value="">Select a country...</option>
            {Object.entries(regions)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([region, countries]) => (
                <optgroup key={region} label={region}>
                  {countries
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([name]) => (
                      <option key={name} value={name}>
                        {name}
                      </option>
                    ))}
                </optgroup>
              ))}
          </select>
        ) : (
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
              fontFamily: "DM Mono, monospace",
              fontSize: "12px",
              color: "#F5F5F5",
              outline: "none",
              transition: "border-color 150ms ease",
            }}
          />
        )}
        <button
          onClick={() =>
            setMode((current) => {
              const next = current === "select" ? "search" : "select"
              if (next === "select") {
                setOpen(false)
                setResults([])
              }
              return next
            })
          }
          style={{
            padding: "8px 10px",
            background: "#0D1B2A",
            border: "1px solid #333333",
            borderRadius: "4px",
            color: "#A3A3A3",
            cursor: "pointer",
            fontSize: "11px",
            fontFamily: "DM Mono, monospace",
            whiteSpace: "nowrap",
          }}
        >
          {mode === "select" ? "Search instead" : "Browse list"}
        </button>
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
            fontFamily: "DM Mono, monospace",
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
                <div style={{ fontFamily: "DM Mono, monospace", fontSize: "12px", color: "#F5F5F5" }}>{name}</div>
                <div style={{ fontFamily: "DM Mono, monospace", fontSize: "10px", color: "#525252" }}>
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
          fontFamily: "DM Mono, monospace",
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
