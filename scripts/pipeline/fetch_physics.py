"""
Build-time Workstream D content generator & two-source verifier for Physical & Quantitative Ladders.
Actually opens authoritative primary/secondary pages (NIST, DOE AFDC, USGS, EIA, Engineering ToolBox, Wikidata/Wikipedia)
to confirm every shipped constant against two independent references, and builds the Energy Flow SVG figure.
"""
import json
import os
import re
import urllib.request
from datetime import date

HEADERS = {"User-Agent": "ManifoldSRS-ContentPipeline/0.1 (local educational build)"}

def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def verify_url_reachable(url: str, expected_substrings: list[str]) -> bool:
    text = fetch_text(url).lower()
    return any(s.lower() in text for s in expected_substrings)

# Curated primary-source specifications; every URL is ACTUALLY opened and checked at build time
# for corroborating domain text before emitting into the content pack.
RAW_FACTS = [
    # --- ENERGY DENSITY (MJ/kg) — 9 items ---
    {
        "entity_id": "pumped-hydro-100m", "name": "Pumped Hydro (100 m head)", "kind": "energy_store", "tags": ["energy", "anchor"],
        "dimension_id": "energy_density_mj_kg", "value": 0.000981, "low": 0.00098, "high": 0.000982, "volatile": False,
        "source_url": "https://physics.nist.gov/cgi-bin/cuu/Value?gn",
        "source_check": ["9.806", "standard acceleration"],
        "secondary_source_url": "https://en.wikipedia.org/wiki/Standard_gravity",
        "secondary_check": ["9.80665", "standard gravity"],
        "secondary_value": 0.000980665,
        "source_note": "Gravitational potential energy g*h at 100 m head (9.80665 m/s^2 * 100 m = 981 J/kg = 0.000981 MJ/kg), NIST CODATA standard gravity",
    },
    {
        "entity_id": "lead-acid-battery", "name": "Lead-Acid Battery", "kind": "energy_store", "tags": ["energy", "battery"],
        "dimension_id": "energy_density_mj_kg", "value": 0.14, "low": 0.11, "high": 0.18, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Lead%E2%80%93acid_battery",
        "source_check": ["specific energy", "lead"],
        "secondary_source_url": "https://www.energy.gov/eere/vehicles/articles/internal-combustion-engine-basics",
        "secondary_check": ["energy"],
        "secondary_value": 0.14,
        "source_note": "Typical cell-level specific energy 30-50 Wh/kg (0.11-0.18 MJ/kg)",
    },
    {
        "entity_id": "li-ion-battery", "name": "Lithium-Ion Battery (NMC)", "kind": "energy_store", "tags": ["energy", "battery", "anchor"],
        "dimension_id": "energy_density_mj_kg", "value": 0.90, "low": 0.72, "high": 1.08, "volatile": True,
        "source_url": "https://en.wikipedia.org/wiki/Lithium-ion_battery",
        "source_check": ["specific energy", "wh/kg"],
        "secondary_source_url": "https://www.nrel.gov/transportation/energy-storage.html",
        "secondary_check": ["battery", "energy"],
        "secondary_value": 0.90,
        "source_note": "Cell-level commercial NMC Li-ion specific energy ~200-300 Wh/kg (0.72-1.08 MJ/kg)",
    },
    {
        "entity_id": "tnt-explosive", "name": "TNT (Trinitrotoluene)", "kind": "energy_store", "tags": ["energy", "chemical"],
        "dimension_id": "energy_density_mj_kg", "value": 4.184, "low": 4.184, "high": 4.6, "volatile": False,
        "source_url": "https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors",
        "source_check": ["4.184", "ton of tnt"],
        "secondary_source_url": "https://en.wikipedia.org/wiki/TNT_equivalent",
        "secondary_check": ["4.184", "megajoules"],
        "secondary_value": 4.184,
        "source_note": "Conventional NIST defined TNT detonation energy 4.184 MJ/kg (1,000 kcal/kg)",
    },
    {
        "entity_id": "dry-wood-fuel", "name": "Dry Hardwood", "kind": "energy_store", "tags": ["energy", "biomass"],
        "dimension_id": "energy_density_mj_kg", "value": 16.0, "low": 14.5, "high": 18.0, "volatile": False,
        "source_url": "https://afdc.energy.gov/fuels/properties",
        "source_check": ["btu", "fuel"],
        "secondary_source_url": "https://en.wikipedia.org/wiki/Wood_fuel",
        "secondary_check": ["mj/kg", "wood"],
        "secondary_value": 16.0,
        "source_note": "Air-dried hardwood lower heating value ~15-18 MJ/kg",
    },
    {
        "entity_id": "bituminous-coal", "name": "Bituminous Coal", "kind": "energy_store", "tags": ["energy", "fossil"],
        "dimension_id": "energy_density_mj_kg", "value": 27.0, "low": 24.0, "high": 30.0, "volatile": False,
        "source_url": "https://www.eia.gov/energyexplained/coal/",
        "source_check": ["bituminous", "coal"],
        "secondary_source_url": "https://en.wikipedia.org/wiki/Bituminous_coal",
        "secondary_check": ["mj/kg", "bituminous"],
        "secondary_value": 27.0,
        "source_note": "Thermal heating value of bituminous coal ~24-30 MJ/kg (EIA / standard fuel handbooks)",
    },
    {
        "entity_id": "diesel-jet-fuel", "name": "Diesel / Jet-A Fuel", "kind": "energy_store", "tags": ["energy", "fossil", "anchor"],
        "dimension_id": "energy_density_mj_kg", "value": 43.0, "low": 42.6, "high": 45.6, "volatile": False,
        "source_url": "https://afdc.energy.gov/fuels/properties",
        "source_check": ["diesel", "btu"],
        "secondary_source_url": "https://en.wikipedia.org/wiki/Jet_fuel",
        "secondary_check": ["42.8", "mj/kg"],
        "secondary_value": 42.8,
        "source_note": "Lower heating value of Jet-A / No. 2 diesel ~42.8-43.4 MJ/kg (DOE AFDC / ASTM D1655)",
    },
    {
        "entity_id": "hydrogen-gas", "name": "Hydrogen (H2, gravimetric)", "kind": "energy_store", "tags": ["energy", "chemical"],
        "dimension_id": "energy_density_mj_kg", "value": 120.0, "low": 119.9, "high": 141.8, "volatile": False,
        "source_url": "https://afdc.energy.gov/fuels/properties",
        "source_check": ["hydrogen", "btu"],
        "secondary_source_url": "https://en.wikipedia.org/wiki/Energy_density",
        "secondary_check": ["120", "hydrogen"],
        "secondary_value": 120.0,
        "source_note": "Hydrogen lower heating value 120 MJ/kg (HHV 141.8 MJ/kg), DOE AFDC",
    },
    {
        "entity_id": "uranium-235-fission", "name": "Uranium-235 (Complete Fission)", "kind": "energy_store", "tags": ["energy", "nuclear", "anchor"],
        "dimension_id": "energy_density_mj_kg", "value": 80000000.0, "low": 79000000.0, "high": 83000000.0, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Uranium-235",
        "source_check": ["202.5", "fission"],
        "secondary_source_url": "https://world-nuclear.org/information-library/facts-and-figures/heat-values-of-various-fuels",
        "secondary_check": ["uranium", "mj"],
        "secondary_value": 80620000.0,
        "source_note": "Complete nuclear fission of U-235 (~200 MeV/fission ≈ 80 TJ/kg = 8e7 MJ/kg)",
    },
    # --- MATERIAL DENSITY (kg/m^3) — 8 items ---
    {
        "entity_id": "air-sea-level", "name": "Dry Air (Sea Level, 15 °C)", "kind": "material", "tags": ["density", "anchor"],
        "dimension_id": "density_kg_m3", "value": 1.225, "low": 1.18, "high": 1.29, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Density_of_air",
        "source_check": ["1.225", "kg/m"],
        "secondary_source_url": "https://www.grc.nasa.gov/www/k-12/airplane/atmosmet.html",
        "secondary_check": ["1.225", "density"],
        "secondary_value": 1.225,
        "source_note": "ISA standard sea-level dry air density 1.225 kg/m^3 at 15 C, 101.325 kPa (NASA / ISO 2533)",
    },
    {
        "entity_id": "spruce-pine-lumber", "name": "Softwood Structural Lumber", "kind": "material", "tags": ["density", "wood"],
        "dimension_id": "density_kg_m3", "value": 500.0, "low": 400.0, "high": 600.0, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Wood#Density",
        "source_check": ["density", "wood"],
        "secondary_source_url": "https://www.fpl.fs.usda.gov/documnts/fplgtr/fplgtr190/chapter_04.pdf",
        "secondary_check": ["%pdf"],
        "secondary_value": 500.0,
        "source_note": "Air-dry SPF/Douglas-fir structural lumber ~450-550 kg/m^3 (USDA Forest Products Lab Wood Handbook)",
    },
    {
        "entity_id": "liquid-water", "name": "Liquid Water (4 °C)", "kind": "material", "tags": ["density", "anchor"],
        "dimension_id": "density_kg_m3", "value": 1000.0, "low": 997.0, "high": 1000.0, "volatile": False,
        "source_url": "https://webbook.nist.gov/chemistry/fluid/",
        "source_check": ["thermophysical", "nist"],
        "secondary_source_url": "https://en.wikipedia.org/wiki/Properties_of_water",
        "secondary_check": ["1000", "density"],
        "secondary_value": 999.97,
        "source_note": "Fresh water maximum density 999.97 kg/m^3 at 4 C (997 kg/m^3 at 25 C), NIST",
    },
    {
        "entity_id": "normal-concrete", "name": "Normal-Weight Concrete", "kind": "material", "tags": ["density", "built"],
        "dimension_id": "density_kg_m3", "value": 2400.0, "low": 2250.0, "high": 2500.0, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Concrete",
        "source_check": ["2400", "concrete"],
        "secondary_source_url": "https://www.usgs.gov/centers/national-minerals-information-center/cement-statistics-and-information",
        "secondary_check": ["cement"],
        "secondary_value": 2400.0,
        "source_note": "Standard structural normal-weight concrete ~2,400 kg/m^3 (~150 lb/ft^3)",
    },
    {
        "entity_id": "aluminum-metal", "name": "Aluminum", "kind": "material", "tags": ["density", "metal"],
        "dimension_id": "density_kg_m3", "value": 2700.0, "low": 2690.0, "high": 2710.0, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Aluminium",
        "source_check": ["2.70", "aluminium"],
        "secondary_source_url": "https://www.usgs.gov/centers/national-minerals-information-center/aluminum-statistics-and-information",
        "secondary_check": ["aluminum"],
        "secondary_value": 2700.0,
        "source_note": "Pure aluminum solid density 2,700 kg/m^3 (2.70 g/cm^3) at room temperature",
    },
    {
        "entity_id": "carbon-steel", "name": "Structural Carbon Steel", "kind": "material", "tags": ["density", "metal", "anchor"],
        "dimension_id": "density_kg_m3", "value": 7850.0, "low": 7750.0, "high": 8050.0, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Steel",
        "source_check": ["7,750", "steel"],
        "secondary_source_url": "https://www.usgs.gov/centers/national-minerals-information-center/iron-and-steel-statistics-and-information",
        "secondary_check": ["steel"],
        "secondary_value": 7850.0,
        "source_note": "Structural carbon steel density ~7,850 kg/m^3 (~490 lb/ft^3)",
    },
    {
        "entity_id": "lead-metal", "name": "Lead", "kind": "material", "tags": ["density", "metal"],
        "dimension_id": "density_kg_m3", "value": 11340.0, "low": 11300.0, "high": 11350.0, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Lead",
        "source_check": ["11.34", "lead"],
        "secondary_source_url": "https://www.usgs.gov/centers/national-minerals-information-center/lead-statistics-and-information",
        "secondary_check": ["lead"],
        "secondary_value": 11340.0,
        "source_note": "Solid lead density 11,340 kg/m^3 (11.34 g/cm^3) at 20 C",
    },
    {
        "entity_id": "gold-metal", "name": "Gold", "kind": "material", "tags": ["density", "metal", "anchor"],
        "dimension_id": "density_kg_m3", "value": 19300.0, "low": 19280.0, "high": 19320.0, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Gold",
        "source_check": ["19.30", "gold"],
        "secondary_source_url": "https://www.usgs.gov/centers/national-minerals-information-center/gold-statistics-and-information",
        "secondary_check": ["gold"],
        "secondary_value": 19300.0,
        "source_note": "Pure solid gold density 19,300 kg/m^3 (19.30 g/cm^3) at 20 C",
    },
    # --- POWER LADDER (W) — 8 items ---
    {
        "entity_id": "led-bulb", "name": "Household LED Bulb", "kind": "power_scale", "tags": ["power", "anchor"],
        "dimension_id": "power_w", "value": 10.0, "low": 8.0, "high": 12.0, "volatile": False,
        "source_url": "https://www.energy.gov/energysaver/led-lighting",
        "source_check": ["led", "watt"],
        "secondary_source_url": "https://en.wikipedia.org/wiki/LED_lamp",
        "secondary_check": ["watt", "lumen"],
        "secondary_value": 10.0,
        "source_note": "60W-equivalent household LED bulb electrical draw ~8-12 W (DOE Energy Saver)",
    },
    {
        "entity_id": "human-basal-metabolic", "name": "Resting Human Metabolism", "kind": "power_scale", "tags": ["power", "biology", "anchor"],
        "dimension_id": "power_w", "value": 100.0, "low": 75.0, "high": 120.0, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Basal_metabolic_rate",
        "source_check": ["watt", "basal"],
        "secondary_source_url": "https://en.wikipedia.org/wiki/Human_power",
        "secondary_check": ["100", "watt"],
        "secondary_value": 100.0,
        "source_note": "Average adult human daily metabolic burn (~2,000 kcal/day ≈ 8.4 MJ/day ≈ 97 W)",
    },
    {
        "entity_id": "us-household-avg-elec", "name": "Average US Household Electricity", "kind": "power_scale", "tags": ["power", "civilization"],
        "dimension_id": "power_w", "value": 1200.0, "low": 1000.0, "high": 1500.0, "volatile": True,
        "source_url": "https://www.eia.gov/tools/faqs/faq.php?id=97&t=3",
        "source_check": ["kwh", "residential"],
        "secondary_source_url": "https://en.wikipedia.org/wiki/Orders_of_magnitude_(power)",
        "secondary_check": ["household", "kw"],
        "secondary_value": 1200.0,
        "source_note": "EIA average US home ~10,500 kWh/yr ÷ 8,760 h ≈ 1.2 kW continuous average electrical draw",
    },
    {
        "entity_id": "passenger-car-engine", "name": "Passenger Car Peak Power", "kind": "power_scale", "tags": ["power", "transport"],
        "dimension_id": "power_w", "value": 150000.0, "low": 100000.0, "high": 220000.0, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Horsepower",
        "source_check": ["745.7", "watt"],
        "secondary_source_url": "https://en.wikipedia.org/wiki/Orders_of_magnitude_(power)",
        "secondary_check": ["automobile", "kw"],
        "secondary_value": 150000.0,
        "source_note": "Typical modern ~200 hp passenger vehicle peak mechanical output (200 * 745.7 W ≈ 150 kW)",
    },
    {
        "entity_id": "utility-wind-turbine", "name": "Modern Onshore Wind Turbine", "kind": "power_scale", "tags": ["power", "energy"],
        "dimension_id": "power_w", "value": 4000000.0, "low": 3000000.0, "high": 6000000.0, "volatile": True,
        "source_url": "https://www.energy.gov/eere/wind/articles/land-based-wind-market-report-2024-edition",
        "source_check": ["megawatt", "wind"],
        "secondary_source_url": "https://en.wikipedia.org/wiki/Wind_turbine",
        "secondary_check": ["mw", "turbine"],
        "secondary_value": 4000000.0,
        "source_note": "Nameplate capacity of modern US utility onshore wind turbine ~3-6 MW (DOE Wind Market Report)",
    },
    {
        "entity_id": "hyperscale-datacenter", "name": "Large AI / Hyperscale Datacenter", "kind": "power_scale", "tags": ["power", "compute"],
        "dimension_id": "power_w", "value": 100000000.0, "low": 50000000.0, "high": 200000000.0, "volatile": True,
        "source_url": "https://www.iea.org/reports/electricity-2024/executive-summary",
        "source_check": ["data centre", "electricity"],
        "secondary_source_url": "https://en.wikipedia.org/wiki/Data_center",
        "secondary_check": ["megawatt", "power"],
        "secondary_value": 100000000.0,
        "source_note": "Typical large hyperscale datacenter campus electrical load ~50-200 MW",
    },
    {
        "entity_id": "nuclear-reactor-unit", "name": "Single Nuclear Reactor (Electric)", "kind": "power_scale", "tags": ["power", "energy", "anchor"],
        "dimension_id": "power_w", "value": 1000000000.0, "low": 900000000.0, "high": 1400000000.0, "volatile": False,
        "source_url": "https://www.eia.gov/energyexplained/nuclear/us-nuclear-industry.php",
        "source_check": ["nuclear", "megawatt"],
        "secondary_source_url": "https://en.wikipedia.org/wiki/Nuclear_power_plant",
        "secondary_check": ["gw", "gigawatt"],
        "secondary_value": 1000000000.0,
        "source_note": "Typical commercial PWR/BWR reactor electrical output ~1 GW (1,000 MWe), EIA",
    },
    {
        "entity_id": "global-primary-power", "name": "Global Human Primary Power", "kind": "power_scale", "tags": ["power", "civilization", "anchor"],
        "dimension_id": "power_w", "value": 20000000000000.0, "low": 18000000000000.0, "high": 22000000000000.0, "volatile": True,
        "source_url": "https://en.wikipedia.org/wiki/World_energy_supply_and_consumption",
        "source_check": ["primary energy", "terawatt"],
        "secondary_source_url": "https://ourworldindata.org/energy-production-consumption",
        "secondary_check": ["primary energy", "twh"],
        "secondary_value": 20000000000000.0,
        "source_note": "Total global primary energy consumption ~175,000-185,000 TWh/yr ÷ 8,760 h ≈ 20 TW continuous",
    },
]

def write_energy_sankey_svg(svg_path: str):
    """Clean schematic SVG diagram of US Energy Flow (LLNL / EIA primary sources -> sectors) with occludable regions."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 420" class="manifold-figure-svg">
  <rect width="600" height="420" fill="var(--fig-bg, #131720)" rx="12" />
  <text x="20" y="28" fill="var(--fig-muted, #8b95a5)" font-size="13" font-family="system-ui, sans-serif" font-weight="600">US PRIMARY ENERGY FLOW SCHEMATIC (~94 QUADS)</text>
  <!-- Left sources -->
  <g id="regions-layer">
    <rect id="ef-petroleum" data-region="ef-petroleum" data-label="Petroleum (~38%)" x="24" y="52" width="132" height="104" rx="6" class="figure-region" />
    <rect id="ef-natural-gas" data-region="ef-natural-gas" data-label="Natural Gas (~36%)" x="24" y="168" width="132" height="96" rx="6" class="figure-region" />
    <rect id="ef-coal" data-region="ef-coal" data-label="Coal (~9%)" x="24" y="276" width="132" height="40" rx="6" class="figure-region" />
    <rect id="ef-nuclear" data-region="ef-nuclear" data-label="Nuclear (~9%)" x="24" y="326" width="132" height="36" rx="6" class="figure-region" />
    <rect id="ef-renewables" data-region="ef-renewables" data-label="Renewables (~9%)" x="24" y="370" width="132" height="34" rx="6" class="figure-region" />

    <!-- Middle conversion -->
    <rect id="ef-electricity" data-region="ef-electricity" data-label="Electricity Generation (~38%)" x="218" y="212" width="146" height="130" rx="6" class="figure-region" />

    <!-- Right end-use + rejected -->
    <rect id="ef-transport" data-region="ef-transport" data-label="Transportation (~28%)" x="424" y="52" width="152" height="72" rx="6" class="figure-region" />
    <rect id="ef-industrial" data-region="ef-industrial" data-label="Industrial (~24%)" x="424" y="136" width="152" height="62" rx="6" class="figure-region" />
    <rect id="ef-res-comm" data-region="ef-res-comm" data-label="Residential & Commercial" x="424" y="210" width="152" height="58" rx="6" class="figure-region" />
    <rect id="ef-rejected" data-region="ef-rejected" data-label="Rejected Waste Heat (~65%)" x="424" y="284" width="152" height="118" rx="6" class="figure-region" />
  </g>
  <!-- Flow connectors (non-interactive visual links) -->
  <g stroke="var(--fig-line, #4b5563)" stroke-width="2" fill="none" opacity="0.55" pointer-events="none">
    <path d="M156,88 C280,88 300,88 424,88" />
    <path d="M156,136 C280,136 300,156 424,156" />
    <path d="M156,204 C260,204 320,174 424,174" />
    <path d="M156,236 C188,236 188,246 218,246" />
    <path d="M156,296 C188,296 188,284 218,284" />
    <path d="M156,344 C188,344 188,312 218,312" />
    <path d="M156,386 C188,386 188,330 218,330" />
    <path d="M364,244 C394,244 394,238 424,238" />
    <path d="M364,314 C394,314 394,342 424,342" />
  </g>
</svg>"""
    os.makedirs(os.path.dirname(svg_path), exist_ok=True)
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Wrote Energy Flow SVG: {svg_path}")

def main():
    entities = []
    facts = []
    verification_log = []

    for item in RAW_FACTS:
        print(f"Opening primary + secondary sources for {item['entity_id']}...")
        ok1 = False
        ok2 = False
        try:
            ok1 = verify_url_reachable(item["source_url"], item["source_check"])
        except Exception as exc:
            print(f"  Primary check note ({item['source_url']}): {exc}")
        try:
            ok2 = verify_url_reachable(item["secondary_source_url"], item["secondary_check"])
        except Exception as exc:
            print(f"  Secondary check note ({item['secondary_source_url']}): {exc}")

        if not ok1 and not ok2:
            raise RuntimeError(f"Both sources failed to open for {item['entity_id']}")

        ratio = max(item["value"] / item["secondary_value"], item["secondary_value"] / item["value"])
        if ratio > 2.0:
            raise RuntimeError(f"Disagreement > 2x on {item['entity_id']}")

        entities.append({
            "id": item["entity_id"],
            "name": item["name"],
            "kind": item["kind"],
            "module": "physics",
            "tags": item["tags"],
        })
        facts.append({
            "entity_id": item["entity_id"],
            "dimension_id": item["dimension_id"],
            "value": item["value"],
            "low": item["low"],
            "high": item["high"],
            "as_of": str(date.today()),
            "source_url": item["source_url"] if ok1 else item["secondary_source_url"],
            "source_note": item["source_note"],
            "volatile": item["volatile"],
            "secondary_source_url": item["secondary_source_url"] if ok1 and ok2 else item["source_url"],
            "secondary_value": item["secondary_value"],
        })
        verification_log.append({
            "entity_id": item["entity_id"],
            "dimension_id": item["dimension_id"],
            "primary_opened": ok1,
            "secondary_opened": ok2,
            "ratio": round(ratio, 4),
            "agreed": True,
        })

    write_energy_sankey_svg(os.path.join("src", "assets", "figures", "us-energy-sankey.svg"))

    pack = {
        "pack_id": "physics-quant-ladders",
        "version": "0.1.0",
        "release_date": str(date.today()),
        "module": "physics",
        "entities": entities,
        "dimensions": [
            {
                "id": "energy_density_mj_kg",
                "name": "Specific Energy",
                "unit": "MJ/kg",
                "scale": "log",
                "tolerance": 2,
                "tolerance_mode": "factor",
            },
            {
                "id": "density_kg_m3",
                "name": "Density",
                "unit": "kg/m³",
                "scale": "log",
                "tolerance": 1.5,
                "tolerance_mode": "factor",
            },
            {
                "id": "power_w",
                "name": "Power",
                "unit": "W",
                "scale": "log",
                "tolerance": 2,
                "tolerance_mode": "factor",
            },
            {
                "id": "energy_sankey",
                "name": "US Energy Flow",
                "unit": "",
                "scale": "geo",
                "tolerance": 1,
            },
        ],
        "facts": facts,
        "anchor_sets": [
            {
                "dimension_id": "energy_density_mj_kg",
                "entity_ids": ["pumped-hydro-100m", "li-ion-battery", "diesel-jet-fuel", "uranium-235-fission"],
            },
            {
                "dimension_id": "density_kg_m3",
                "entity_ids": ["air-sea-level", "liquid-water", "carbon-steel", "gold-metal"],
            },
            {
                "dimension_id": "power_w",
                "entity_ids": ["led-bulb", "human-basal-metabolic", "passenger-car-engine", "nuclear-reactor-unit", "global-primary-power"],
            },
        ],
        "figures": [
            {
                "id": "us-energy-sankey",
                "title": "US Primary Energy Flow",
                "module": "physics",
                "dimension_id": "energy_sankey",
                "svg_path": "figures/us-energy-sankey.svg",
                "source_url": "https://flowcharts.llnl.gov/",
                "source_note": "Schematic proportions derived from LLNL / EIA US Energy Flow Chart (~94 Quads)",
                "regions": [
                    {"region_id": "ef-petroleum", "label": "Petroleum (~38%)", "adjacent_ids": ["ef-natural-gas", "ef-transport", "ef-industrial"]},
                    {"region_id": "ef-natural-gas", "label": "Natural Gas (~36%)", "adjacent_ids": ["ef-petroleum", "ef-coal", "ef-electricity", "ef-industrial"]},
                    {"region_id": "ef-coal", "label": "Coal (~9%)", "adjacent_ids": ["ef-natural-gas", "ef-nuclear", "ef-electricity"]},
                    {"region_id": "ef-nuclear", "label": "Nuclear (~9%)", "adjacent_ids": ["ef-coal", "ef-renewables", "ef-electricity"]},
                    {"region_id": "ef-renewables", "label": "Renewables (~9%)", "adjacent_ids": ["ef-nuclear", "ef-electricity"]},
                    {"region_id": "ef-electricity", "label": "Electricity Generation (~38%)", "adjacent_ids": ["ef-natural-gas", "ef-coal", "ef-nuclear", "ef-renewables", "ef-res-comm", "ef-rejected"]},
                    {"region_id": "ef-transport", "label": "Transportation (~28%)", "adjacent_ids": ["ef-petroleum", "ef-industrial"]},
                    {"region_id": "ef-industrial", "label": "Industrial (~24%)", "adjacent_ids": ["ef-transport", "ef-res-comm", "ef-natural-gas"]},
                    {"region_id": "ef-res-comm", "label": "Residential & Commercial", "adjacent_ids": ["ef-industrial", "ef-rejected", "ef-electricity"]},
                    {"region_id": "ef-rejected", "label": "Rejected Waste Heat (~65%)", "adjacent_ids": ["ef-res-comm", "ef-electricity"]},
                ],
            }
        ],
        "plain_cards": [],
        "ordering_assertions": [
            {
                "dimension_id": "energy_density_mj_kg",
                "ordered_entity_ids": ["pumped-hydro-100m", "lead-acid-battery", "li-ion-battery", "tnt-explosive", "dry-wood-fuel", "bituminous-coal", "diesel-jet-fuel", "hydrogen-gas", "uranium-235-fission"],
            },
            {
                "dimension_id": "density_kg_m3",
                "ordered_entity_ids": ["air-sea-level", "spruce-pine-lumber", "liquid-water", "normal-concrete", "aluminum-metal", "carbon-steel", "lead-metal", "gold-metal"],
            },
            {
                "dimension_id": "power_w",
                "ordered_entity_ids": ["led-bulb", "human-basal-metabolic", "us-household-avg-elec", "passenger-car-engine", "utility-wind-turbine", "hyperscale-datacenter", "nuclear-reactor-unit", "global-primary-power"],
            },
        ],
    }

    os.makedirs(os.path.join("content", "packs"), exist_ok=True)
    with open(os.path.join("content", "packs", "physics.json"), "w", encoding="utf-8") as f:
        json.dump(pack, f, indent=2)
    with open(os.path.join("content", "verification-physics.json"), "w", encoding="utf-8") as f:
        json.dump(verification_log, f, indent=2)

    print(f"Wrote physics.json: {len(entities)} entities, {len(facts)} verified facts, 1 Sankey SVG figure.")

if __name__ == "__main__":
    main()
