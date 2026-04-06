"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import Navbar from "@/components/layout/Navbar"
import ActionProposal from "@/components/sim/ActionProposal"
import DiplomacyPanel from "@/components/sim/DiplomacyPanel"
import EndScreen from "@/components/sim/EndScreen"
import GeoMap from "@/components/sim/GeoMap"
import GridMap from "@/components/sim/GridMap"
import InsightsPanel from "@/components/sim/InsightsPanel"
import KpiPanel from "@/components/sim/KpiPanel"
import SimControls from "@/components/sim/SimControls"
import SimHeader from "@/components/sim/SimHeader"
import Timeline from "@/components/sim/Timeline"
import { api } from "@/lib/api"
import { useSimStore } from "@/store/simStore"

const WEIGHTS = {
  power_plant: 0.25,
  water_treatment: 0.2,
  hospital: 0.2,
  telecom_tower: 0.05,
  transport_hub: 0.1,
  fuel_depot: 0.05,
  shelter: 0.05,
  command_center: 0.1,
}

function computeCoverage(assets, nation) {
  const nationAssets = (assets || []).filter((asset) => asset.nation === nation)
  let score = 0
  for (const asset of nationAssets) {
    const weight = WEIGHTS[asset.asset_type] ?? 0
    const fraction = asset.is_destroyed ? 0 : asset.health / asset.max_health
    score += weight * fraction
  }
  return Math.min(1, score)
}

function computeCoverageMap(state) {
  const assets = state?.assets || []
  const nations = state?.nations || ["Auria", "Boros"]
  return Object.fromEntries(nations.map((nation) => [nation, computeCoverage(assets, nation)]))
}

function BackendErrorPanel({ message, onRetry }) {
  return (
    <div className="max-w-4xl mx-auto rounded border border-[#EF4444] p-8 font-mono text-sm text-[#EF4444] space-y-4">
      <p>{message}</p>
      <p>Backend unavailable. Start the FastAPI server:</p>
      <pre className="text-[#A3A3A3]">uvicorn backend.main:app --reload --port 8000</pre>
      <button onClick={onRetry} className="rounded border border-[#333333] px-4 py-2 text-[#F5F5F5]">Retry</button>
    </div>
  )
}

function LoadingGridSkeleton() {
  return (
    <div className="mx-auto flex h-[640px] w-[640px] max-w-full animate-pulse items-center justify-center rounded border border-[#333333] bg-[#212020]">
      <p className="font-mono text-sm text-[#525252]">Loading scenario...</p>
    </div>
  )
}

export default function SimulationPage() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const hasAutoLoaded = useRef(false)
  const profiles = useSimStore((s) => s.profiles)
  const geoNations = useSimStore((s) => s.geoNations)
  const scenarioPath = useSimStore((s) => s.scenarioPath)
  const simState = useSimStore((s) => s.simState)
  const coverageMap = useSimStore((s) => s.coverageMap)
  const history = useSimStore((s) => s.history)
  const eventLog = useSimStore((s) => s.eventLog)
  const endConditions = useSimStore((s) => s.endConditions)
  const isTerminal = useSimStore((s) => s.isTerminal)
  const isRunning = useSimStore((s) => s.isRunning)
  const autoStep = useSimStore((s) => s.autoStep)
  const stepDelay = useSimStore((s) => s.stepDelay)
  const selectedAsset = useSimStore((s) => s.selectedAsset)
  const nationFilter = useSimStore((s) => s.nationFilter)
  const turnPhase = useSimStore((s) => s.turnPhase)
  const proposedActions = useSimStore((s) => s.proposedActions)
  const lastNarrative = useSimStore((s) => s.lastNarrative)
  const setProfiles = useSimStore((s) => s.setProfiles)
  const setScenario = useSimStore((s) => s.setScenario)
  const setSimState = useSimStore((s) => s.setSimState)
  const setNarrative = useSimStore((s) => s.setNarrative)
  const setIsRunning = useSimStore((s) => s.setIsRunning)
  const setAutoStep = useSimStore((s) => s.setAutoStep)
  const setStepDelay = useSimStore((s) => s.setStepDelay)
  const setNationFilter = useSimStore((s) => s.setNationFilter)
  const setTurnPhase = useSimStore((s) => s.setTurnPhase)
  const setProposedActions = useSimStore((s) => s.setProposedActions)
  const clearProposal = useSimStore((s) => s.clearProposal)
  const resetStore = useSimStore((s) => s.reset)
  const [previousState, setPreviousState] = useState(null)
  const [errorMessage, setErrorMessage] = useState("")
  const [isScenarioLoading, setIsScenarioLoading] = useState(false)

  const scenariosQuery = useQuery({
    queryKey: ["scenarios"],
    queryFn: api.listScenarios,
    retry: 2,
    retryDelay: 1000,
  })

  const profilesQuery = useQuery({
    queryKey: ["profiles", "sim"],
    queryFn: api.getProfiles,
    retry: 2,
    retryDelay: 1000,
  })

  useEffect(() => {
    if (profilesQuery.data && Object.keys(profiles || {}).length === 0) {
      setProfiles(profilesQuery.data)
    }
  }, [profiles, profilesQuery.data, setProfiles])

  const profilesReady = Object.keys(profiles || {}).length > 0
  const scenarios = scenariosQuery.data?.scenarios || []

  useEffect(() => {
    if (scenariosQuery.isSuccess && scenarios.length > 0 && profilesReady && !simState && !isRunning && !hasAutoLoaded.current) {
      hasAutoLoaded.current = true
      const firstScenario = scenarios[0]
      ;(async () => {
        try {
          setIsRunning(true)
          setIsScenarioLoading(true)
          const response = await api.loadScenario(firstScenario.path, true, useSimStore.getState().profiles, useSimStore.getState().geoNations)
          const dipResult = await api.initDiplomacy(response.state, useSimStore.getState().profiles, useSimStore.getState().geoNations)
          const nextCoverage = computeCoverageMap(dipResult.state)
          setScenario(firstScenario.path, firstScenario)
          setSimState(dipResult.state, null, nextCoverage)
          setPreviousState(null)
        } catch (error) {
          setErrorMessage(error.message || "Failed to load scenario")
        } finally {
          setIsRunning(false)
          setIsScenarioLoading(false)
        }
      })()
    }
  }, [isRunning, profilesReady, scenarios, scenariosQuery.isSuccess, setIsRunning, setScenario, setSimState, simState])

  useEffect(() => {
    if (profilesQuery.isSuccess && Object.keys(profilesQuery.data?.profiles || {}).length === 0) {
      router.replace("/setup")
    }
  }, [profilesQuery.data, profilesQuery.isSuccess, router])

  const loadScenario = async (path) => {
    if (!path) return
    try {
      setErrorMessage("")
      setIsRunning(true)
      setIsScenarioLoading(true)
      clearProposal()
      const selected = scenarios.find((item) => item.path === path) || null
      const response = await api.loadScenario(path, true, useSimStore.getState().profiles, useSimStore.getState().geoNations)
      const dipResult = await api.initDiplomacy(response.state, useSimStore.getState().profiles, useSimStore.getState().geoNations)
      const nextCoverage = computeCoverageMap(dipResult.state)
      setScenario(path, selected)
      setPreviousState(null)
      setSimState(dipResult.state, null, nextCoverage)
    } catch (error) {
      setErrorMessage(error.message || "Failed to load scenario")
    } finally {
      setIsRunning(false)
      setIsScenarioLoading(false)
    }
  }

  async function proposeTurn() {
    const store = useSimStore.getState()
    if (store.isRunning || store.simState?.is_terminal) return
    setTurnPhase("proposing")
    try {
      const result = await api.proposeActions(store.simState)
      setProposedActions(result.proposed_actions, result.reasoning)
      setTurnPhase("reviewing")
    } catch (error) {
      console.error("Propose failed:", error)
      setErrorMessage(error.message || "Propose failed")
      setTurnPhase("idle")
    }
  }

  async function executeTurn(confirmedActions) {
    setTurnPhase("executing")
    setIsRunning(true)
    try {
      const previous = useSimStore.getState().simState
      const result = await api.stepSimulation(previous, confirmedActions)
      const nextCoverage = computeCoverageMap(result.state)
      setPreviousState(previous)
      useSimStore.getState().setSimState(result.state, result, nextCoverage)
      useSimStore.getState().setNarrative(result.turn, result.narrative)
      useSimStore.getState().clearProposal()
      if (result.is_terminal) setAutoStep(false)
    } catch (error) {
      console.error("Execute failed:", error)
      setErrorMessage(error.message || "Execute failed")
    } finally {
      setIsRunning(false)
      setTurnPhase("idle")
    }
  }

  function cancelProposal() {
    clearProposal()
  }

  async function onRestart() {
    const store = useSimStore.getState()
    const path = store.scenarioPath
    if (!path) return
    const preservedProfiles = store.profiles
    const preservedGeo = store.geoNations
    const selectedMeta = scenarios.find((item) => item.path === path) || null
    resetStore()
    useSimStore.getState().setProfiles(preservedProfiles)
    useSimStore.getState().setGeoNations(preservedGeo)
    setPreviousState(null)
    setIsScenarioLoading(true)
    try {
      const result = await api.loadScenario(path, true, preservedProfiles, preservedGeo)
      const dipResult = await api.initDiplomacy(result.state, preservedProfiles, preservedGeo)
      const nextCoverage = computeCoverageMap(dipResult.state)
      useSimStore.getState().setScenario(path, selectedMeta)
      useSimStore.getState().setSimState(dipResult.state, null, nextCoverage)
    } catch (error) {
      setErrorMessage(error.message || "Failed to restart scenario")
    } finally {
      setIsScenarioLoading(false)
    }
  }

  const resetScenario = async () => {
    if (!scenarioPath) return
    hasAutoLoaded.current = true
    await loadScenario(scenarioPath)
  }

  useEffect(() => {
    if (!autoStep || !simState || isRunning || isTerminal || turnPhase !== "idle") return undefined
    const timer = window.setTimeout(() => {
      proposeTurn().then(() => {
        window.setTimeout(() => {
          const store = useSimStore.getState()
          if (store.turnPhase === "reviewing") {
            executeTurn(store.proposedActions)
          }
        }, 800)
      })
    }, stepDelay)
    return () => window.clearTimeout(timer)
  }, [autoStep, simState, isRunning, isTerminal, stepDelay, turnPhase])

  const coverage = useMemo(() => {
    if (coverageMap && Object.keys(coverageMap).length > 0) return coverageMap
    if (simState) return computeCoverageMap(simState)
    return { Auria: 1, Boros: 1 }
  }, [coverageMap, simState])

  const previousCoverage = useMemo(() => {
    if (history.length > 1) return history[history.length - 2].service_coverage || {}
    return coverage
  }, [coverage, history])

  if (profilesQuery.isLoading || scenariosQuery.isLoading) {
    return (
      <main className="min-h-screen bg-[#0A0A0A] pt-20 px-6">
        <Navbar />
        <div className="max-w-4xl mx-auto rounded border border-[#333333] p-8 font-mono text-sm text-[#A3A3A3]">Loading country profiles from backend...</div>
      </main>
    )
  }

  if (profilesQuery.isError || scenariosQuery.isError) {
    return (
      <main className="min-h-screen bg-[#0A0A0A] pt-20 px-6">
        <Navbar />
        <BackendErrorPanel
          message={profilesQuery.error?.message || scenariosQuery.error?.message || "Failed to reach backend."}
          onRetry={() => {
            queryClient.invalidateQueries({ queryKey: ["profiles"] })
            queryClient.invalidateQueries({ queryKey: ["profiles", "sim"] })
            queryClient.invalidateQueries({ queryKey: ["scenarios"] })
          }}
        />
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-[#0A0A0A]">
      <Navbar />
      <div className="pt-14">
        <SimHeader scenarioName={simState?.scenario_name || "Simulation"} turn={simState?.turn || 0} maxTurns={simState?.max_turns || 60} coverage={coverage} />
        <div className="max-w-[1680px] mx-auto px-6 py-6">
          {errorMessage ? <div className="mb-4 rounded border border-[#EF4444] p-3 text-sm font-mono text-[#EF4444]">{errorMessage}</div> : null}
          <div className="grid grid-cols-[280px_minmax(0,1fr)_380px] items-start gap-6">
            <SimControls
              scenarios={scenarios}
              scenarioPath={scenarioPath}
              simState={simState}
              isRunning={isRunning}
              isTerminal={isTerminal}
              autoStep={autoStep}
              stepDelay={stepDelay}
              nationFilter={nationFilter}
              turnPhase={turnPhase}
              onScenarioChange={loadScenario}
              onProposeTurn={proposeTurn}
              onReset={resetScenario}
              onAutoStepChange={setAutoStep}
              onStepDelayChange={setStepDelay}
              onNationFilterChange={setNationFilter}
            />

            <div className="space-y-3">
              {!simState || isScenarioLoading ? (
                <LoadingGridSkeleton />
              ) : (
                <>
                  {simState?.metadata?.["_has_geo"] ? (
                    <GeoMap
                      onAssetClick={(id) => useSimStore.getState().setSelectedAsset(id)}
                      proposedActions={proposedActions}
                      nationFilter={nationFilter}
                    />
                  ) : (
                    <GridMap simState={simState} nationFilter={nationFilter} onAssetClick={(id) => useSimStore.getState().setSelectedAsset(id)} />
                  )}
                  {turnPhase === "reviewing" ? <ActionProposal onExecute={executeTurn} onCancel={cancelProposal} /> : null}
                  <InsightsPanel />
                  <Timeline history={history} />
                  <DiplomacyPanel />
                </>
              )}
            </div>

            <KpiPanel
              simState={simState}
              previousState={previousState}
              profiles={profiles}
              selectedAssetId={selectedAsset}
              coverageMap={coverage}
              previousCoverageMap={previousCoverage}
              eventLog={eventLog}
              endConditions={endConditions}
              lastNarrative={lastNarrative}
            />
          </div>
        </div>
        <EndScreen onRestart={onRestart} />
      </div>
    </main>
  )
}
