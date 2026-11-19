# First-principles source map (2026-11-19)

Produced by a deliberately "no background knowledge" research pass: derive what magnitude intuition needs, then find primary material to load. Verification status is noted per source; "recalled" = not opened this session.

## The generative set

**Operators (skills, not facts):** dimensional analysis; log-space estimation (geometric mean of bounds, Fermi decomposition); square–cube scaling (strength ∝ L², weight ∝ L³ → span/depth, slenderness); stock = flow × residence time; per-capita × population = total; power × time = energy; efficiency chains.

**Physical anchors (~15):** human 1.7 m / 70 kg / ~100 W / ~8 MJ·day⁻¹ / 1.4 m/s walk; Earth radius 6,400 km (circumference 40,000 km); g ≈ 10; water 1 t/m³; air 1.2 kg/m³; 1 atm ≈ 10⁵ Pa ≈ 10 m water; c; solar constant ~1.4 kW/m² (~1 kW/m² at ground); fuels ~40 MJ/kg vs batteries ~0.5 MJ/kg; Avogadro, k_B; age of universe / Earth.

**Human-world anchors (~8):** world population ~8 B; world GDP ~$100 T; world primary energy ~600 EJ/yr (≈2.5 kW/person, ~10 kW/American); per-person steel/cement/food flows; CO₂/person; lifespan.

**Building anchors:** loads 10–100 psf; span/depth by system; floor-to-floor; sf/person occupant density; egress in/person; U/R values; W/sf lighting & plug; sf/ton cooling; $/sf by type; fee/schedule %.

**Classes:** anchor (used to check other numbers) · derivable (one operator step from anchors) · trivia · **exact convention** (code values: not derivable, must not be tolerance-graded).

## Load these first

| # | source | status | format | covers |
|---|---|---|---|---|
| 1 | NIST CODATA 2022 — physics.nist.gov/cuu/Constants/Table/allascii.txt | primary, free, verified | text | constants |
| 2 | Our World in Data — docs.owid.io (Charts/Tables APIs, CSV per chart) | aggregator citing primaries; CC BY (site) | API/CSV | per-capita energy, CO₂, GDP, food |
| 3 | World Bank WDI API v2 — api.worldbank.org/v2 | primary, free, verified | JSON | country + World totals |
| 4 | UN World Population Prospects 2024 — population.un.org/wpp/downloads | primary, CC BY 3.0 IGO (page not opened) | CSV | population, fertility, life expectancy |
| 5 | Energy Institute Statistical Review 2026 — energyinst.org/statistical-review | primary, free (xlsx not opened) | xlsx | energy by fuel/country → joules ladder |
| 6 | USGS Mineral Commodity Summaries 2026 — pubs.usgs.gov/publication/mcs2026 (data DOI 10.5066/P1WKQ63T) | primary, public domain, verified via search | PDF/CSV | steel, cement, copper, aggregates |
| 7 | 2010 ADA Standards — ada.gov/law-and-regs/design-standards/2010-stds/ | primary, free, verified | HTML/PDF | accessibility dimensions |
| 8 | ICC Digital Codes, IBC 2021 free view | primary, read-only (fetch refused; recalled) | web | egress, occupancy, heights/areas |
| 9 | NCARB ARE 5.0 Handbook + Guidelines — ncarb.org/ARE5 | primary, free; **current edition not verified** (404 during research) | PDF | exam scope |
| 10 | Allen & Iano, *The Architect's Studio Companion* 7th ed. (Wiley) | paid; based on 2021 IBC (retailer listings) | book | structural/MEP sizing rules of thumb (charts from p. 55) |

## The rest

- Mahajan, *The Art of Insight* — open access (OAPEN / MIT Press), verified; licence conflict (title page CC BY-NC-SA vs DOAB CC BY) → treat as NC-SA. *Street-Fighting Mathematics* — recalled as free, CC BY-NC-SA. Operators, not facts.
- MacKay, *Sustainable Energy – Without the Hot Air* — withouthotair.com, recalled free for personal use (non-CC). Best per-capita kWh/day framing.
- *Cell Biology by the Numbers* / BioNumbers — book.bionumbers.org, free draft, verified; no licence stated.
- NASA Planetary Fact Sheet — public domain, verified (updated 2026-11-13).
- EIA Open Data APIv2 — free with key, verified; CBECS/RECS energy-use intensity by building type.
- NIST Chemistry WebBook, IMF WEO — primary, free (recalled).
- Engineering Toolbox — secondary, unclear sourcing; cross-check only.
- Paywalled: ASCE 7 (free ASCE Hazard Tool for site loads, recalled), ICC A117.1-2017, AIA documents (free samples/commentaries), Architectural Graphic Standards, Ching, Allen & Iano *Fundamentals*, Ballast, Amber Book, Black Spectacles.
- Idea books (paid, not loadable): Smil, Weinstein & Adam *Guesstimation*, Swartz, Rosling *Factfulness*, Munroe. Jeff Dean latency numbers: no primary home, c. 2012, flag if used. Eames *Powers of Ten*: framing, not data.

## Conceptual holes in the app

1. No per-capita layer or World totals (kWh/day, kg CO₂, t materials, m² floor per person).
2. No flows/rates/residence times (only Mt/yr); no growth/doubling.
3. No money ladder ($/sf by type, $/kWh, $/t steel, project cost bands).
4. No structural rules of thumb (span/depth by system, typical spans, column sizes) — the ARE's quantitative core.
5. No building energy / MEP magnitudes (U-values, EUI, W/sf, sf/ton, cfm/person, footcandles).
6. No absolute-energy ladder or efficiencies (engine, PV, heat-pump COP, LED lm/W).
7. No operator cards (dimensional analysis, geometric-mean estimation, scaling exponents).
8. Empty architect's band (1 mm–30 cm, ~10³ Pa) — symptom of 4–5.
9. Exact-convention vs magnitude not modelled as a type (partly addressed: `dimension.drill = false`).
10. No human-body / biological rate anchors (metabolic power, heart rate, reaction time).
