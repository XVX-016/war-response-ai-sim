"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import Navbar from "@/components/layout/Navbar"
import CountrySearch from "@/components/setup/CountrySearch"
import CountrySliders from "@/components/setup/CountrySliders"
import RadarChart from "@/components/setup/RadarChart"
import ComparisonTable from "@/components/setup/ComparisonTable"
import { api } from "@/lib/api"
import { useSimStore } from "@/store/simStore"

function createEmptyProfile(nation) {
  return {
    nation,
    display_name: "Select a country",
    flag_emoji: nation === "Auria" ? "A" : "B",
    lore: "Choose a country from the dropdown to load its real-world profile.",
    gdp_index: 0.5,
    military_strength: 0.5,
    population_millions: 5,
    resource_richness: 0.5,
    terrain_difficulty: 0.5,
    alliance_strength: 0.5,
    pending_selection: true,
  }
}

const EMPTY_SETUP_PROFILES = {
  Auria: createEmptyProfile("Auria"),
  Boros: createEmptyProfile("Boros"),
}

function StartSimulationButton() {
  const router = useRouter()
  const profiles = useSimStore((s) => s.profiles)
  const geoNations = useSimStore((s) => s.geoNations)
  const setScenario = useSimStore((s) => s.setScenario)
  const setSimState = useSimStore((s) => s.setSimState)
  const hasProfiles = Object.keys(profiles || {}).length > 0
  const hasSelections = Boolean(geoNations?.Auria && geoNations?.Boros)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState("")

  const handleStart = async () => {
    if (!hasProfiles || isSaving) return
    if (!hasSelections) {
      setError("Choose both countries from the dropdowns before starting the simulation.")
      return
    }
    setIsSaving(true)
    try {
      setError("")
      await Promise.all(
        Object.entries(profiles).map(([nation, profile]) => api.saveProfile(nation, profile))
      )
      const scenariosResult = await api.listScenarios()
      const firstScenario = scenariosResult.scenarios?.[0]
      if (firstScenario?.path) {
        const loadResult = await api.loadScenario(firstScenario.path, true, profiles, geoNations)
        const dipResult = await api.initDiplomacy(loadResult.state, profiles, geoNations)
        setScenario(firstScenario.path, firstScenario)
        setSimState(dipResult.state, null)
      }
      router.push("/sim")
    } catch (err) {
      console.error("Start simulation failed:", err)
      setError(err.message || "Failed to start simulation")
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <>
      <button
        disabled={isSaving || !hasSelections}
        onClick={handleStart}
        className="px-8 py-3 bg-[#3B82F6] text-white text-sm font-mono tracking-widest uppercase border border-[#3B82F6] rounded hover:bg-[#1D4ED8] transition-colors"
        style={{ opacity: isSaving || !hasSelections ? 0.5 : 1, cursor: isSaving || !hasSelections ? "not-allowed" : "pointer" }}
      >
        {isSaving ? "Loading..." : "Start Simulation"}
      </button>
      {!hasSelections && !error ? <p className="text-sm text-[#525252] mt-3">Select both countries to enable geographic simulation.</p> : null}
      {error ? <p className="text-sm text-[#EF4444] mt-3">{error}</p> : null}
    </>
  )
}

function BackendErrorPanel({ message, onRetry }) {
  return (
    <div className="border border-[#EF4444] rounded p-8 text-[#EF4444] font-mono text-sm space-y-4">
      <p>{message}</p>
      <p>Backend unavailable. Start the FastAPI server:</p>
      <pre className="text-[#A3A3A3]">uvicorn backend.main:app --reload --port 8000</pre>
      <button onClick={onRetry} className="px-4 py-2 border border-[#333333] rounded text-[#F5F5F5]">
        Retry
      </button>
    </div>
  )
}

export default function SetupPage() {
  const queryClient = useQueryClient()
  const setProfiles = useSimStore((s) => s.setProfiles)
  const updateProfile = useSimStore((s) => s.updateProfile)
  const geoNations = useSimStore((s) => s.geoNations)
  const setGeoNations = useSimStore((s) => s.setGeoNations)
  const profiles = useSimStore((s) => s.profiles)
  const [errorMessage, setErrorMessage] = useState("")

  const { isLoading, isError, error } = useQuery({
    queryKey: ["profiles"],
    queryFn: api.getProfiles,
    retry: 2,
    retryDelay: 1000,
  })

  useEffect(() => {
    setProfiles(EMPTY_SETUP_PROFILES)
    setGeoNations({})
  }, [setGeoNations, setProfiles])

  const ready = Object.keys(profiles || {}).length > 0

  return (
    <main className="min-h-screen bg-[#0A0A0A] pt-20 pb-16 px-6">
      <Navbar />
      <div className="max-w-7xl mx-auto">
        <div className="mb-12">
          <p className="text-xs font-mono tracking-[0.2em] uppercase text-[#525252] mb-2">Configuration</p>
          <h1 className="text-4xl font-bold text-[#F5F5F5] tracking-tight">Country Setup</h1>
          <p className="text-sm text-[#525252] mt-2">
            Configure each nation before starting the simulation. Parameters scale starting resources, agent capability,
            and simulation dynamics.
          </p>
        </div>

        {isLoading && !ready ? (
          <div className="border border-[#333333] rounded p-8 text-[#A3A3A3] font-mono text-sm">Loading country profiles from backend...</div>
        ) : null}

        {isError ? (
          <BackendErrorPanel
            message={error?.message || "Failed to load country profiles from backend."}
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["profiles"] })}
          />
        ) : null}

        {ready ? (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-16">
              <div>
                <CountrySearch
                  accentColour="#3B82F6"
                  onSelect={(profile, selectedCountryName) => {
                    updateProfile("Auria", { ...profiles.Auria, ...profile, nation: "Auria", pending_selection: false })
                    setGeoNations({ ...geoNations, Auria: selectedCountryName })
                  }}
                />
                <CountrySliders nation="Auria" accentColour="#3B82F6" onError={setErrorMessage} />
              </div>
              <div>
                <CountrySearch
                  accentColour="#F59E0B"
                  onSelect={(profile, selectedCountryName) => {
                    updateProfile("Boros", { ...profiles.Boros, ...profile, nation: "Boros", pending_selection: false })
                    setGeoNations({ ...geoNations, Boros: selectedCountryName })
                  }}
                />
                <CountrySliders nation="Boros" accentColour="#F59E0B" onError={setErrorMessage} />
              </div>
            </div>

            {(!profiles?.Auria?.pending_selection || !profiles?.Boros?.pending_selection) && (
              <div className="border-t border-[#1F1F1F] pt-16">
                <p className="text-xs font-mono tracking-[0.2em] uppercase text-[#525252] mb-2">Analysis</p>
                <h2 className="text-2xl font-bold text-[#F5F5F5] mb-10 tracking-tight">Country Comparison</h2>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-stretch">
                  <RadarChart />
                  <ComparisonTable />
                </div>
              </div>
            )}

            <div className="mt-16 flex flex-col items-center gap-4">
              {errorMessage ? <p className="text-sm text-[#EF4444] font-mono">{errorMessage}</p> : null}
              <StartSimulationButton />
            </div>
          </>
        ) : null}
      </div>
    </main>
  )
}
