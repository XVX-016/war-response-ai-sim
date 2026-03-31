"use client"

import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import Navbar from "@/components/layout/Navbar"
import GridMap from "@/components/sim/GridMap"
import KpiPanel from "@/components/sim/KpiPanel"
import SimControls from "@/components/sim/SimControls"
import SimHeader from "@/components/sim/SimHeader"
import Timeline from "@/components/sim/Timeline"
import { api } from "@/lib/api"
import { useSimStore } from "@/store/simStore"

export default function SimulationPage() {
  const router = useRouter()
  const profiles = useSimStore((s) => s.profiles)
  const scenarioPath = useSimStore((s) => s.scenarioPath)
  const simState = useSimStore((s) => s.simState)
  const history = useSimStore((s) => s.history)
  const isRunning = useSimStore((s) => s.isRunning)
  const autoStep = useSimStore((s) => s.autoStep)
  const stepDelay = useSimStore((s) => s.stepDelay)
  const selectedAsset = useSimStore((s) => s.selectedAsset)
  const nationFilter = useSimStore((s) => s.nationFilter)
  const setProfiles = useSimStore((s) => s.setProfiles)
  const setScenario = useSimStore((s) => s.setScenario)
  const setSimState = useSimStore((s) => s.setSimState)
  const setIsRunning = useSimStore((s) => s.setIsRunning)
  const setAutoStep = useSimStore((s) => s.setAutoStep)
  const setStepDelay = useSimStore((s) => s.setStepDelay)
  const setNationFilter = useSimStore((s) => s.setNationFilter)
  const resetStore = useSimStore((s) => s.reset)
  const [previousState, setPreviousState] = useState(null)
  const [errorMessage, setErrorMessage] = useState("")

  const scenariosQuery = useQuery({
    queryKey: ["scenarios"],
    queryFn: api.listScenarios,
  })

  const profilesQuery = useQuery({
    queryKey: ["profiles", "sim"],
    queryFn: api.getProfiles,
    enabled: !profiles || Object.keys(profiles).length === 0,
  })

  useEffect(() => {
    if (profilesQuery.data?.profiles) {
      setProfiles(profilesQuery.data.profiles)
    }
  }, [profilesQuery.data, setProfiles])

  const profilesReady = Object.keys(profiles || {}).length > 0
  const scenarios = scenariosQuery.data?.scenarios || []

  useEffect(() => {
    if (!profilesReady && profilesQuery.isFetched && !profilesQuery.isLoading && !profilesQuery.data?.profiles) {
      router.replace("/setup")
    }
  }, [profilesReady, profilesQuery.data, profilesQuery.isFetched, profilesQuery.isLoading, router])

  const loadScenario = async (path) => {
    if (!path) return
    try {
      setErrorMessage("")
      setIsRunning(true)
      resetStore()
      const response = await api.loadScenario(path, true, profiles)
      setScenario(path, scenarios.find((item) => item.path === path) || null)
      setPreviousState(null)
      setSimState(response.state)
    } catch (error) {
      setErrorMessage(error.message || "Failed to load scenario")
    } finally {
      setIsRunning(false)
    }
  }

  const stepOneTurn = async () => {
    if (!simState || isRunning || simState.is_terminal) return
    try {
      setErrorMessage("")
      setIsRunning(true)
      const currentState = simState
      const result = await api.stepSimulation(currentState, "auto")
      setPreviousState(currentState)
      setSimState(result.state, result)
      if (result.is_terminal) setAutoStep(false)
    } catch (error) {
      setErrorMessage(error.message || "Failed to step simulation")
      setAutoStep(false)
    } finally {
      setIsRunning(false)
    }
  }

  useEffect(() => {
    if (!autoStep || !simState || isRunning || simState.is_terminal) return undefined
    const timer = window.setTimeout(() => {
      stepOneTurn()
    }, stepDelay)
    return () => window.clearTimeout(timer)
  }, [autoStep, simState, isRunning, stepDelay])

  const coverage = useMemo(() => {
    if (history.length > 0) return history[history.length - 1].service_coverage || {}
    const fallback = {}
    ;(simState?.nations || []).forEach((nation) => {
      fallback[nation] = 1
    })
    return fallback
  }, [history, simState])

  const previousCoverage = useMemo(() => {
    if (history.length > 1) return history[history.length - 2].service_coverage || {}
    return coverage
  }, [coverage, history])

  if (!profilesReady && profilesQuery.isLoading) {
    return (
      <main className="min-h-screen bg-[#0A0A0A] pt-20 px-6">
        <Navbar />
        <div className="max-w-4xl mx-auto border border-[#333333] rounded p-8 text-[#A3A3A3] font-mono text-sm">
          Loading country profiles from backend...
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-[#0A0A0A]">
      <Navbar />
      <div className="pt-14">
        <SimHeader scenarioName={simState?.scenario_name || "Simulation"} turn={simState?.turn || 0} maxTurns={simState?.max_turns || 60} coverage={coverage} />
        <div className="px-6 py-6 max-w-[1680px] mx-auto">
          {errorMessage ? <div className="mb-4 border border-[#EF4444] rounded p-3 text-sm font-mono text-[#EF4444]">{errorMessage}</div> : null}
          <div className="grid grid-cols-[280px_minmax(0,1fr)_380px] gap-6 items-start">
            <SimControls
              scenarios={scenarios}
              scenarioPath={scenarioPath}
              simState={simState}
              isRunning={isRunning}
              autoStep={autoStep}
              stepDelay={stepDelay}
              nationFilter={nationFilter}
              onScenarioChange={loadScenario}
              onAdvance={stepOneTurn}
              onReset={() => loadScenario(scenarioPath)}
              onAutoStepChange={setAutoStep}
              onStepDelayChange={setStepDelay}
              onNationFilterChange={setNationFilter}
            />

            <div className="space-y-6">
              {!simState ? (
                <div className="border border-[#333333] rounded p-12 bg-[#212020] text-center text-[#525252] font-mono">
                  Select a scenario to begin the simulation.
                </div>
              ) : (
                <>
                  <GridMap simState={simState} nationFilter={nationFilter} />
                  <Timeline history={history} />
                </>
              )}
            </div>

            <KpiPanel simState={simState} previousState={previousState} profiles={profiles} selectedAssetId={selectedAsset} coverageMap={coverage} previousCoverageMap={previousCoverage} />
          </div>
        </div>
      </div>
    </main>
  )
}
