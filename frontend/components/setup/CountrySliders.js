"use client"

import { useState } from "react"
import { api } from "@/lib/api"
import { useSimStore } from "@/store/simStore"

const FACTORS = [
  { key: "gdp_index", label: "GDP Index", min: 0, max: 1, step: 0.05 },
  { key: "military_strength", label: "Military Strength", min: 0, max: 1, step: 0.05 },
  { key: "population_millions", label: "Population (millions)", min: 0.5, max: 50, step: 0.5 },
  { key: "resource_richness", label: "Resource Richness", min: 0, max: 1, step: 0.05 },
  { key: "terrain_difficulty", label: "Terrain Difficulty", min: 0, max: 1, step: 0.05 },
  { key: "alliance_strength", label: "Alliance Strength", min: 0, max: 1, step: 0.05 },
]

function deriveLabel(profile, key) {
  const v = profile?.[key] ?? 0
  if (key === "gdp_index") return v < 0.25 ? "Low" : v < 0.5 ? "Medium" : v < 0.75 ? "High" : "Very High"
  if (key === "military_strength") return v < 0.25 ? "Limited" : v < 0.5 ? "Moderate" : v < 0.75 ? "Strong" : "Elite"
  if (key === "terrain_difficulty") return v < 0.25 ? "Flat / Urban" : v < 0.5 ? "Mixed" : v < 0.75 ? "Mountainous" : "Extreme"
  if (key === "alliance_strength") return v < 0.25 ? "Isolated" : v < 0.5 ? "Neutral" : v < 0.75 ? "Allied" : "Major Alliance"
  if (key === "resource_richness") return v < 0.35 ? "Scarce" : v < 0.65 ? "Moderate" : "Rich"
  if (key === "population_millions") return `${Number(v).toFixed(1)}M`
  return ""
}

export default function CountrySliders({ nation, accentColour, onError }) {
  const profiles = useSimStore((s) => s.profiles)
  const setProfiles = useSimStore((s) => s.setProfiles)
  const [toast, setToast] = useState("")
  const profile = profiles?.[nation]

  if (!profile) {
    return <div className="border border-[#333333] rounded p-6 text-[#525252]">Loading {nation}...</div>
  }

  const showToast = (message, tone = "success") => {
    setToast(`${tone}:${message}`)
    window.setTimeout(() => setToast(""), 1800)
  }

  const onReset = async () => {
    try {
      const data = await api.getProfiles()
      setProfiles(data)
      showToast("Reset to defaults")
      onError?.("")
    } catch (error) {
      onError?.(error.message || "Failed to reset profiles")
    }
  }

  const onSave = async () => {
    try {
      await api.saveProfile(nation, profile)
      showToast("Saved")
      onError?.("")
    } catch (error) {
      onError?.(error.message || "Failed to save profile")
    }
  }

  const [tone, message] = toast ? toast.split(":") : ["", ""]

  return (
    <div className="border border-[#333333] rounded p-6 bg-[#0A0A0A]">
      <div className="flex items-center gap-3 mb-3">
        <span className="inline-flex items-center justify-center rounded w-7 h-7 font-mono text-xs font-semibold text-white" style={{ backgroundColor: accentColour }}>
          {nation === "Auria" ? "A" : "B"}
        </span>
        <div>
          <h3 className="text-xl font-semibold text-[#F5F5F5]">{profile.display_name}</h3>
        </div>
      </div>
      <p className="text-sm text-[#525252] mb-4">{profile.lore}</p>
      <div className="border-t border-[#1F1F1F] mb-5" />

      <div className="space-y-5">
        {FACTORS.map((factor) => {
          const value = Number(profile[factor.key] ?? 0)
          const decimals = factor.step < 1 ? (factor.step === 0.5 ? 1 : 2) : 0
          return (
            <div key={factor.key}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-[#A3A3A3]">{factor.label}</span>
                <span className="text-sm font-mono" style={{ color: accentColour }}>{value.toFixed(decimals)}</span>
              </div>
              <input
                type="range"
                min={factor.min}
                max={factor.max}
                step={factor.step}
                value={value}
                onChange={(e) => {
                  const updatedProfile = { ...profile, [factor.key]: Number(e.target.value) }
                  useSimStore.getState().updateProfile(nation, updatedProfile)
                }}
                className="w-full accent-current"
                style={{ accentColor: accentColour }}
              />
              <div className="mt-2 inline-block text-[10px] font-mono uppercase tracking-[0.15em] px-2 py-1 rounded border border-[#333333] text-[#A3A3A3]">
                {deriveLabel(profile, factor.key)}
              </div>
            </div>
          )
        })}
      </div>

      <div className="flex gap-3 mt-6">
        <button onClick={onReset} className="flex-1 px-4 py-2 border border-[#333333] rounded text-xs font-mono uppercase tracking-widest text-[#A3A3A3] hover:text-white hover:border-[#525252] transition-colors">
          Reset to defaults
        </button>
        <button onClick={onSave} className="flex-1 px-4 py-2 border rounded text-xs font-mono uppercase tracking-widest text-white transition-colors" style={{ borderColor: accentColour, backgroundColor: accentColour }}>
          Save profile
        </button>
      </div>
      {message ? <p className={`mt-3 text-xs font-mono uppercase tracking-[0.15em] ${tone === "success" ? "text-[#22C55E]" : "text-[#EF4444]"}`}>{message}</p> : null}
    </div>
  )
}
