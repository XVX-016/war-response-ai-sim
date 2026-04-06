const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

async function apiFetch(path, options = {}) {
  const isFormData = options.body instanceof FormData
  const headers = isFormData
    ? { ...(options.headers || {}) }
    : { "Content-Type": "application/json", ...(options.headers || {}) }

  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `API error ${res.status}`)
  }
  return res.json()
}

export const api = {
  health: () => apiFetch("/api/health"),
  listScenarios: () => apiFetch("/api/scenarios"),
  getProfiles: () => apiFetch("/api/country/profiles"),
  saveProfile: (nation, profile) =>
    apiFetch("/api/country/profile", {
      method: "POST",
      body: JSON.stringify({ nation, profile }),
    }),
  loadScenario: (path, apply_profiles, profiles, geo_nations = undefined) =>
    apiFetch("/api/scenario/load", {
      method: "POST",
      body: JSON.stringify({ path, apply_profiles, profiles, geo_nations }),
    }),
  stepSimulation: (state, actions = "auto") =>
    apiFetch("/api/scenario/step", {
      method: "POST",
      body: JSON.stringify({ state, actions }),
    }),
  initDiplomacy: (state, profiles, geo_nations = undefined) =>
    apiFetch("/api/scenario/init-diplomacy", {
      method: "POST",
      body: JSON.stringify({ state, profiles, geo_nations }),
    }),
  proposeActions: (state) =>
    apiFetch("/api/scenario/propose", {
      method: "POST",
      body: JSON.stringify({ state }),
    }),
  listGeoCountries: () => apiFetch("/api/geo/countries"),
  buildScenario: (preset, seed, name) =>
    apiFetch("/api/scenario/build", {
      method: "POST",
      body: JSON.stringify({ preset, seed, name }),
    }),
  detectVision: (file) => {
    const form = new FormData()
    form.append("file", file)
    return apiFetch("/api/vision/detect", {
      method: "POST",
      headers: {},
      body: form,
    })
  },
}
