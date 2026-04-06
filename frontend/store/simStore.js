import { create } from "zustand"

function normaliseProfiles(input) {
  if (!input) return {}
  if (input.profiles && typeof input.profiles === "object") {
    return input.profiles
  }
  return input
}

export const useSimStore = create((set) => ({
  profiles: {},
  setProfiles: (input) => set({ profiles: normaliseProfiles(input) }),
  updateProfile: (nation, profile) =>
    set((s) => ({ profiles: { ...s.profiles, [nation]: profile } })),

  scenarioPath: null,
  scenarioMeta: null,
  setScenario: (path, meta) => set({ scenarioPath: path, scenarioMeta: meta }),
  geoNations: {},
  setGeoNations: (geoNations) => set({ geoNations }),

  simState: null,
  coverageMap: {},
  history: [],
  eventLog: [],
  endConditions: {},
  isTerminal: false,
  lastNarrative: "",
  narrativeHistory: [],
  isRunning: false,
  autoStep: false,
  stepDelay: 1000,
  selectedAsset: null,
  nationFilter: "All",
  turnPhase: "idle",
  proposedActions: [],
  actionReasonings: [],

  setEventLog: (log) => set({ eventLog: log ?? [] }),
  setNarrative: (turn, text) =>
    set((s) => ({
      lastNarrative: text || "",
      narrativeHistory: text ? [...s.narrativeHistory, { turn, text }] : s.narrativeHistory,
    })),
  setTurnPhase: (phase) => set({ turnPhase: phase }),
  setProposedActions: (actions, reasonings) =>
    set({
      proposedActions: actions ?? [],
      actionReasonings: reasonings ?? [],
    }),
  clearProposal: () =>
    set({
      proposedActions: [],
      actionReasonings: [],
      turnPhase: "idle",
    }),

  setSimState: (newState, result, coverageMap = null) =>
    set((s) => ({
      simState: newState,
      coverageMap: coverageMap ?? s.coverageMap,
      eventLog: newState?.event_log ?? [],
      endConditions: newState?.end_conditions_met ?? s.endConditions,
      isTerminal: result?.is_terminal ?? newState?.is_terminal ?? s.isTerminal,
      history: result
        ? [
            ...s.history,
            {
              turn: result.turn,
              service_coverage: result.service_coverage ?? coverageMap ?? s.coverageMap,
              total_displaced: result.total_displaced,
              end_condition: result.end_condition,
            },
          ]
        : s.history,
    })),

  setAutoStep: (v) => set({ autoStep: v }),
  setStepDelay: (v) => set({ stepDelay: v }),
  setSelectedAsset: (id) => set({ selectedAsset: id }),
  setIsRunning: (v) => set({ isRunning: v }),
  setNationFilter: (v) => set({ nationFilter: v }),

  reset: () =>
    set({
      scenarioPath: null,
      scenarioMeta: null,
      simState: null,
      coverageMap: {},
      history: [],
      eventLog: [],
      endConditions: {},
      isTerminal: false,
      lastNarrative: "",
      narrativeHistory: [],
      isRunning: false,
      autoStep: false,
      selectedAsset: null,
      nationFilter: "All",
      turnPhase: "idle",
      proposedActions: [],
      actionReasonings: [],
    }),
}))
