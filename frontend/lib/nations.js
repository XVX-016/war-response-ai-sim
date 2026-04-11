"use client"

import { useSimStore } from "@/store/simStore"

export function useNationDisplayName(internalName) {
  const geoNations = useSimStore((s) => s.geoNations)
  return geoNations?.[internalName] || internalName
}

export function useNationDisplayNames() {
  const simState = useSimStore((s) => s.simState)
  const geoNations = useSimStore((s) => s.geoNations)
  return (simState?.nations ?? []).map((nation) => ({
    internal: nation,
    display: geoNations?.[nation] || nation,
  }))
}
