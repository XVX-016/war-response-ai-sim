import { create } from "zustand"

export const useSimStore = create((set) => ({
  profiles: {},
  setProfiles: (profiles) => set({ profiles }),
  updateProfile: (nation, profile) =>
    set((s) => ({ profiles: { ...s.profiles, [nation]: profile } })),

  scenarioPath: null,
  scenarioMeta: null,
  setScenario: (path, meta) => set({ scenarioPath: path, scenarioMeta: meta }),

  simState: null,
  history: [],
  isRunning: false,
  autoStep: false,
  stepDelay: 1000,
  selectedAsset: null,
  nationFilter: "All",

  setSimState: (newState, result) =>
    set((s) => ({
      simState: newState,
      history: result
        ? [
            ...s.history,
            {
              turn: result.turn,
              service_coverage: result.service_coverage,
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
      simState: null,
      history: [],
      isRunning: false,
      autoStep: false,
      selectedAsset: null,
      nationFilter: "All",
    }),
}))
