export async function loadCountryCache() {
  try {
    const response = await fetch("/api/countries")
    const data = await response.json()
    return data.countries || {}
  } catch {
    return {}
  }
}

export function countryToProfile(countryName, countryData) {
  return {
    nation: countryName,
    display_name: countryName,
    flag_emoji: countryData.flag || "🏳",
    lore:
      `${countryName} - ${countryData.region}. `
      + `GDP index: ${countryData.gdp_index}, `
      + `Military: ${countryData.military_strength}.`,
    gdp_index: countryData.gdp_index,
    military_strength: countryData.military_strength,
    population_millions: countryData.population_millions,
    resource_richness: countryData.resource_richness,
    terrain_difficulty: countryData.terrain_difficulty,
    alliance_strength: countryData.alliance_strength,
  }
}
