# Country Profiles

Each JSON file defines one nation's profile for ResilienceSim.
Filename must match the nation name in lowercase: `auria.json` for nation "Auria".

Fields:
- `gdp_index` (0?1): Economic output. Scales repair crew stocks and medical/food resupply.
- `military_strength` (0?1): Logistics and engineering capacity. Scales repair crews and agent action budget.
- `population_millions` (float > 0): Raw population in millions. Scales zone populations.
- `resource_richness` (0?1): Natural resource endowment. Scales fuel, generators, water purifiers.
- `terrain_difficulty` (0?1): Geographic obstacle level. Reduces transport hub starting health and increases transport dependency penalties.
- `alliance_strength` (0?1): External support network. Provides bonus resupply per turn and reduces exogenous event probability.

To add a custom country: copy auria.json, rename it, change the values.
The simulator will auto-detect any .json file in this directory.
