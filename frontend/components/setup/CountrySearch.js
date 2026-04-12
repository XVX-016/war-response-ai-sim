"use client"

import { useEffect, useState } from "react"
import { countryToProfile, loadCountryCache } from "@/lib/countries"
import { useSimStore } from "@/store/simStore"

export default function CountrySearch({ onSelect }) {
  const [cache, setCache] = useState({})
  const [selectedCountry, setSelectedCountry] = useState("")
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

  function handleSelect(countryName, countryData) {
    const profile = countryToProfile(countryName, countryData)
    onSelect(profile, countryName)
    setSelectedCountry(countryName)
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
      </div>

      <div
        style={{
          fontFamily: "DM Mono, monospace",
          fontSize: "9px",
          color: "#333333",
          marginTop: "4px",
          letterSpacing: "0.05em",
        }}
      >
        {Object.keys(cache).length} countries loaded - World Bank data
      </div>
    </div>
  )
}
