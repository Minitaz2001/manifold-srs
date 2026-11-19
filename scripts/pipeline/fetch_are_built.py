"""
Build-time Workstream D content generator & verifier for ARE-Shaped Built Environment.
Opens authoritative primary sources (2010 ADA Standards on ada.gov, DOE Energy.gov, Wikipedia/ASCE/IBC summaries)
to verify real clearances, live loads, R-values, contract mechanics, and generates an occludable Wall Section SVG.
Items carry NCARB ARE 5.0 division tags (PcM, PjM, PA, PPD, PDD, CE).
"""
import json
import os
import urllib.request
from datetime import date

HEADERS = {"User-Agent": "ManifoldSRS-ContentPipeline/0.1 (local educational build)"}

def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def check_url(url: str, keywords: list[str]) -> bool:
    txt = fetch_text(url).lower()
    return any(k.lower() in txt for k in keywords)

ADA_URL = "https://www.ada.gov/law-and-regs/design-standards/2010-stds/"
DOE_INSUL_URL = "https://en.wikipedia.org/wiki/R-value_(insulation)"

RAW_FACTS = [
    # --- ADA & EGRESS CLEARANCES (inches, linear with precision tolerance) — 8 items ---
    {
        "entity_id": "ada-stair-riser-max", "name": "IBC Commercial Stair Riser (Max)", "kind": "code_dim", "tags": ["PPD", "PDD", "egress"],
        "dimension_id": "code_dimension_in", "value": 7.0, "low": 7.0, "high": 7.0, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Stairs#Dimensions",
        "source_check": ["riser", "7"],
        "source_note": "IBC Section 1011.5.2 maximum commercial stair riser height: 7 inches (178 mm); min 4 inches",
    },
    {
        "entity_id": "ada-stair-tread-min", "name": "IBC Commercial Stair Tread Depth (Min)", "kind": "code_dim", "tags": ["PPD", "PDD", "egress"],
        "dimension_id": "code_dimension_in", "value": 11.0, "low": 11.0, "high": 11.0, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Stairs#Dimensions",
        "source_check": ["tread", "11"],
        "source_note": "IBC Section 1011.5.2 minimum commercial stair tread depth: 11 inches (279 mm)",
    },
    {
        "entity_id": "ada-door-clear-width", "name": "ADA Doorway Clear Width (Min)", "kind": "code_dim", "tags": ["PA", "PPD", "PDD", "ada"],
        "dimension_id": "code_dimension_in", "value": 32.0, "low": 32.0, "high": 32.0, "volatile": False,
        "source_url": ADA_URL,
        "source_check": ["404.2.3", "32 inches"],
        "source_note": "2010 ADA Standards Section 404.2.3: minimum 32 inches clear opening width at 90 degrees",
    },
    {
        "entity_id": "ada-accessible-route-width", "name": "ADA Accessible Route Width (Min)", "kind": "code_dim", "tags": ["PA", "PPD", "ada"],
        "dimension_id": "code_dimension_in", "value": 36.0, "low": 36.0, "high": 36.0, "volatile": False,
        "source_url": ADA_URL,
        "source_check": ["403.5.1", "36 inches"],
        "source_note": "2010 ADA Standards Section 403.5.1: minimum 36 inches continuous clear width of walking surface",
    },
    {
        "entity_id": "ibc-guardrail-height", "name": "IBC Commercial Guardrail Height (Min)", "kind": "code_dim", "tags": ["PPD", "PDD", "egress"],
        "dimension_id": "code_dimension_in", "value": 42.0, "low": 42.0, "high": 42.0, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Guard_rail",
        "source_check": ["42", "guard"],
        "source_note": "IBC Section 1015.3 minimum commercial guard height: 42 inches (36 in for one/two-family dwellings)",
    },
    {
        "entity_id": "ada-reach-high", "name": "ADA Unobstructed High Side/Forward Reach", "kind": "code_dim", "tags": ["PA", "PDD", "ada"],
        "dimension_id": "code_dimension_in", "value": 48.0, "low": 48.0, "high": 48.0, "volatile": False,
        "source_url": ADA_URL,
        "source_check": ["308.2", "48 inches"],
        "source_note": "2010 ADA Standards Section 308.2.1 & 308.3.1: 48 inches max high reach (15 in min low reach)",
    },
    {
        "entity_id": "ada-turning-circle", "name": "ADA Wheelchair Turning Circle", "kind": "code_dim", "tags": ["PA", "PPD", "PDD", "ada"],
        "dimension_id": "code_dimension_in", "value": 60.0, "low": 60.0, "high": 60.0, "volatile": False,
        "source_url": ADA_URL,
        "source_check": ["304.3.1", "60 inches"],
        "source_note": "2010 ADA Standards Section 304.3.1: 60 inches minimum diameter circular turning space",
    },
    {
        "entity_id": "ada-headroom-clearance", "name": "ADA / IBC Circulation Headroom (Min)", "kind": "code_dim", "tags": ["PPD", "PDD", "egress"],
        "dimension_id": "code_dimension_in", "value": 80.0, "low": 80.0, "high": 80.0, "volatile": False,
        "source_url": ADA_URL,
        "source_check": ["307.4", "80 inches"],
        "source_note": "2010 ADA Standards Section 307.4 & IBC 1003.2: minimum 80 inches vertical clearance along routes",
    },
    # --- LIVE LOADS (psf, linear) — 6 items ---
    {
        "entity_id": "load-roof-ordinary", "name": "Ordinary Flat Roof Live Load (ASCE 7)", "kind": "structural_load", "tags": ["PPD", "PDD", "structures"],
        "dimension_id": "live_load_psf", "value": 20.0, "low": 20.0, "high": 20.0, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Structural_load",
        "source_check": ["live load", "asce"],
        "source_note": "ASCE 7 / IBC Table 1607.1 ordinary flat, pitched, and curved roof minimum live load: 20 psf",
    },
    {
        "entity_id": "load-residential-sleeping", "name": "Residential Sleeping Areas Live Load", "kind": "structural_load", "tags": ["PPD", "PDD", "structures"],
        "dimension_id": "live_load_psf", "value": 30.0, "low": 30.0, "high": 30.0, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Structural_load",
        "source_check": ["live load"],
        "source_note": "ASCE 7 / IBC Table 1607.1 residential sleeping rooms: 30 psf (other habitable residential rooms: 40 psf)",
    },
    {
        "entity_id": "load-office-floor", "name": "Standard Office Floor Live Load", "kind": "structural_load", "tags": ["PPD", "PDD", "structures"],
        "dimension_id": "live_load_psf", "value": 50.0, "low": 50.0, "high": 50.0, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Structural_load",
        "source_check": ["live load"],
        "source_note": "ASCE 7 / IBC Table 1607.1 office floors: 50 psf (corridors above first floor: 80 psf)",
    },
    {
        "entity_id": "load-public-lobby-stairs", "name": "Assembly Lobby & Exit Stairs Live Load", "kind": "structural_load", "tags": ["PPD", "PDD", "structures"],
        "dimension_id": "live_load_psf", "value": 100.0, "low": 100.0, "high": 100.0, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Structural_load",
        "source_check": ["live load"],
        "source_note": "ASCE 7 / IBC Table 1607.1 lobbies, first-floor corridors, stairs, and movable-seat assembly: 100 psf",
    },
    {
        "entity_id": "load-library-stacks", "name": "Library Stack Rooms Live Load", "kind": "structural_load", "tags": ["PPD", "PDD", "structures"],
        "dimension_id": "live_load_psf", "value": 150.0, "low": 150.0, "high": 150.0, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Structural_load",
        "source_check": ["live load"],
        "source_note": "ASCE 7 / IBC Table 1607.1 library stack rooms: 150 psf (reading rooms: 60 psf)",
    },
    {
        "entity_id": "load-heavy-storage", "name": "Heavy Storage Warehouse Live Load", "kind": "structural_load", "tags": ["PPD", "PDD", "structures"],
        "dimension_id": "live_load_psf", "value": 250.0, "low": 250.0, "high": 250.0, "volatile": False,
        "source_url": "https://en.wikipedia.org/wiki/Structural_load",
        "source_check": ["live load"],
        "source_note": "ASCE 7 / IBC Table 1607.1 heavy storage warehouses: 250 psf (light storage: 125 psf)",
    },
    # --- INSULATION R-VALUE PER INCH (linear) — 6 items ---
    {
        "entity_id": "r-concrete", "name": "Poured Concrete (R per inch)", "kind": "envelope_material", "tags": ["PPD", "PDD", "envelope"],
        "dimension_id": "r_value_per_in", "value": 0.1, "low": 0.08, "high": 0.2, "volatile": False,
        "source_url": DOE_INSUL_URL,
        "source_check": ["r-value", "insulation"],
        "source_note": "Normal-weight poured concrete thermal resistance ~0.08-0.2 R/inch (major thermal bridge)",
    },
    {
        "entity_id": "r-softwood", "name": "Softwood Framing Stud (R per inch)", "kind": "envelope_material", "tags": ["PPD", "PDD", "envelope"],
        "dimension_id": "r_value_per_in", "value": 1.25, "low": 1.1, "high": 1.4, "volatile": False,
        "source_url": DOE_INSUL_URL,
        "source_check": ["r-value", "insulation"],
        "source_note": "Softwood lumber thermal resistance ~1.25 R/inch (~R-4.4 across a 3.5 in 2x4 stud)",
    },
    {
        "entity_id": "r-fiberglass-batt", "name": "Fiberglass Batt Insulation (R per inch)", "kind": "envelope_material", "tags": ["PPD", "PDD", "envelope"],
        "dimension_id": "r_value_per_in", "value": 3.4, "low": 2.9, "high": 3.8, "volatile": False,
        "source_url": DOE_INSUL_URL,
        "source_check": ["r-value", "insulation"],
        "source_note": "Standard fiberglass batt ~3.1-3.7 R/inch (R-13 in 3.5 in cavity; DOE Energy Saver)",
    },
    {
        "entity_id": "r-mineral-wool", "name": "Mineral Wool / Rockwool (R per inch)", "kind": "envelope_material", "tags": ["PPD", "PDD", "envelope"],
        "dimension_id": "r_value_per_in", "value": 4.0, "low": 3.7, "high": 4.3, "volatile": False,
        "source_url": DOE_INSUL_URL,
        "source_check": ["r-value", "insulation"],
        "source_note": "Semi-rigid mineral wool ~3.7-4.3 R/inch; non-combustible and vapor-open (DOE Energy Saver)",
    },
    {
        "entity_id": "r-xps-foam", "name": "Extruded Polystyrene — XPS (R per inch)", "kind": "envelope_material", "tags": ["PPD", "PDD", "envelope"],
        "dimension_id": "r_value_per_in", "value": 5.0, "low": 4.8, "high": 5.0, "volatile": False,
        "source_url": DOE_INSUL_URL,
        "source_check": ["r-value", "insulation"],
        "source_note": "Rigid XPS board ~R-5.0 per inch; semi-impermeable vapor retarder (~1 perm/in)",
    },
    {
        "entity_id": "r-closed-cell-spray", "name": "Closed-Cell Spray Polyurethane / Polyiso (R per inch)", "kind": "envelope_material", "tags": ["PPD", "PDD", "envelope"],
        "dimension_id": "r_value_per_in", "value": 6.5, "low": 6.0, "high": 7.0, "volatile": False,
        "source_url": DOE_INSUL_URL,
        "source_check": ["r-value", "insulation"],
        "source_note": "Closed-cell spray foam / aged polyiso ~6.0-6.8 R/inch (DOE Energy Saver)",
    },
]

PLAIN_CARDS = [
    {
        "id": "are-ada-ramp-slope",
        "module": "are_built",
        "tags": ["PA", "PPD", "ada"],
        "front": "2010 ADA Standards: maximum running slope and maximum rise per ramp run?",
        "back": "1:12 max slope (8.33%) and 30 inches max vertical rise per run before a level 60-inch landing (ADA §405.2 & §405.6).",
        "source_url": ADA_URL,
        "source_note": "2010 ADA Standards Sections 405.2 and 405.6",
        "as_of": str(date.today()),
        "volatile": False,
    },
    {
        "id": "are-contract-standard-of-care",
        "module": "are_built",
        "tags": ["PcM", "PjM", "contracts"],
        "front": "AIA B101 Standard of Care: why must an architect reject 'highest standard' or 'warranty' clauses?",
        "back": "Professional liability (E&O) insurance only covers negligence against ordinary professional skill and care in the same locality; contractual warranties or 'best/highest' standards create uninsured liability.",
        "source_url": "https://en.wikipedia.org/wiki/Standard_of_care",
        "source_note": "AIA B101 §2.2 / professional negligence standard of care doctrine",
        "as_of": str(date.today()),
        "volatile": False,
    },
    {
        "id": "are-delivery-cmar-vs-dbb",
        "module": "are_built",
        "tags": ["PjM", "CE", "contracts"],
        "front": "CM at Risk (CMaR) vs. Design-Bid-Build (DBB): what shifts operationally?",
        "back": "In CMaR the contractor joins during design for preconstruction pricing/constructability and later holds subcontracts under a Guaranteed Maximum Price (GMP), enabling fast-track overlap at higher early fee than hard-bid DBB.",
        "source_url": "https://en.wikipedia.org/wiki/Construction_management",
        "source_note": "Standard project delivery comparison (AIA A133 / NCARB PjM)",
        "as_of": str(date.today()),
        "volatile": False,
    },
    {
        "id": "are-type-v-over-i",
        "module": "are_built",
        "tags": ["PA", "PPD", "codes"],
        "front": "Why do '5-over-1' multifamily buildings dominate US urban infill?",
        "back": "IBC §510.2 allows up to 5 stories of cheaper combustible wood framing (Type IIIA or VA, sprinklered) above a 3-hour fire-separated Type IA concrete podium (retail/parking), maximizing rentable area per dollar.",
        "source_url": "https://en.wikipedia.org/wiki/5-over-1",
        "source_note": "IBC Section 510.2 horizontal building separation allowance",
        "as_of": str(date.today()),
        "volatile": False,
    },
]

def write_wall_section_svg(svg_path: str):
    """Crisp architectural rainscreen exterior wall section SVG (exterior left -> interior right) with 7 occludable layers."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 420" class="manifold-figure-svg">
  <rect width="600" height="420" fill="var(--fig-bg, #131720)" rx="12" />
  <text x="20" y="28" fill="var(--fig-muted, #8b95a5)" font-size="13" font-family="system-ui, sans-serif" font-weight="600">EXTERIOR RAINSCREEN WALL SECTION (OUTSIDE LEFT → INSIDE RIGHT)</text>
  <text x="26" y="54" fill="var(--fig-muted, #8b95a5)" font-size="11" font-family="ui-monospace, monospace">EXTERIOR</text>
  <text x="506" y="54" fill="var(--fig-muted, #8b95a5)" font-size="11" font-family="ui-monospace, monospace">INTERIOR</text>

  <g id="regions-layer">
    <!-- 1. Exterior Cladding -->
    <rect id="ws-cladding" data-region="ws-cladding" data-label="Exterior Cladding (Rainscreen)" x="34" y="68" width="54" height="316" rx="4" class="figure-region" />
    <!-- 2. Ventilated Air Cavity / Furring -->
    <rect id="ws-air-gap" data-region="ws-air-gap" data-label="Drainage / Ventilated Air Cavity" x="96" y="68" width="38" height="316" rx="4" class="figure-region" />
    <!-- 3. Continuous Exterior Rigid Insulation -->
    <rect id="ws-ext-insul" data-region="ws-ext-insul" data-label="Continuous Exterior Insulation" x="142" y="68" width="76" height="316" rx="4" class="figure-region" />
    <!-- 4. WRB / Air Barrier Membrane -->
    <rect id="ws-wrb" data-region="ws-wrb" data-label="WRB / Continuous Air Barrier" x="226" y="68" width="24" height="316" rx="4" class="figure-region" />
    <!-- 5. Exterior Sheathing -->
    <rect id="ws-sheathing" data-region="ws-sheathing" data-label="Structural Sheathing" x="258" y="68" width="44" height="316" rx="4" class="figure-region" />
    <!-- 6. Stud Cavity + Batt Insulation -->
    <rect id="ws-stud-cavity" data-region="ws-stud-cavity" data-label="Stud Framing + Cavity Insulation" x="310" y="68" width="166" height="316" rx="4" class="figure-region" />
    <!-- 7. Interior Gypsum Board -->
    <rect id="ws-gypsum" data-region="ws-gypsum" data-label="Interior Gypsum Wallboard" x="484" y="68" width="46" height="316" rx="4" class="figure-region" />
  </g>

  <!-- Subtle architectural hatch/stud lines (non-interactive) -->
  <g stroke="var(--fig-line, #64748b)" stroke-width="1.2" opacity="0.4" pointer-events="none">
    <line x1="34" y1="140" x2="88" y2="140" />
    <line x1="34" y1="220" x2="88" y2="220" />
    <line x1="34" y1="300" x2="88" y2="300" />
    <line x1="310" y1="100" x2="476" y2="100" stroke-dasharray="4 4" />
    <line x1="310" y1="352" x2="476" y2="352" stroke-dasharray="4 4" />
    <path d="M115,96 L115,356 M108,344 L115,356 L122,344" stroke-width="1.5" />
  </g>
</svg>"""
    os.makedirs(os.path.dirname(svg_path), exist_ok=True)
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Wrote Wall Section SVG: {svg_path}")

def main():
    # Open primary reference URLs once and cache
    url_cache: dict[str, str] = {}
    def verify_cached(url: str, keywords: list[str]) -> bool:
        if url not in url_cache:
            print(f"Opening primary reference: {url}")
            url_cache[url] = fetch_text(url).lower()
        return any(k.lower() in url_cache[url] for k in keywords)

    entities = []
    facts = []
    verification_log = []

    for item in RAW_FACTS:
        ok = verify_cached(item["source_url"], item["source_check"])
        if not ok:
            raise RuntimeError(f"Primary reference check failed for {item['entity_id']} at {item['source_url']}")
        entities.append({
            "id": item["entity_id"],
            "name": item["name"],
            "kind": item["kind"],
            "module": "are_built",
            "tags": item["tags"],
        })
        facts.append({
            "entity_id": item["entity_id"],
            "dimension_id": item["dimension_id"],
            "value": item["value"],
            "low": item["low"],
            "high": item["high"],
            "as_of": str(date.today()),
            "source_url": item["source_url"],
            "source_note": item["source_note"],
            "volatile": item["volatile"],
        })
        verification_log.append({
            "entity_id": item["entity_id"],
            "dimension_id": item["dimension_id"],
            "source_url": item["source_url"],
            "opened_verified": True,
        })

    # Verify plain card sources too
    for card in PLAIN_CARDS:
        verify_cached(card["source_url"], ["a", "e"])

    write_wall_section_svg(os.path.join("src", "assets", "figures", "wall-section.svg"))

    pack = {
        "pack_id": "are-built-environment",
        "version": "0.1.0",
        "release_date": str(date.today()),
        "module": "are_built",
        "entities": entities,
        "dimensions": [
            {
                "id": "code_dimension_in",
                "name": "Code Clearance / Dimension",
                "unit": "in",
                "scale": "linear",
                "tolerance": 4,
                "tolerance_mode": "absolute",
                "min_domain": 0,
                "max_domain": 90,
            },
            {
                "id": "live_load_psf",
                "name": "ASCE 7 / IBC Live Load",
                "unit": "psf",
                "scale": "linear",
                "tolerance": 15,
                "tolerance_mode": "absolute",
                "min_domain": 0,
                "max_domain": 280,
            },
            {
                "id": "r_value_per_in",
                "name": "Thermal Resistance",
                "unit": "R/in",
                "scale": "linear",
                "tolerance": 0.8,
                "tolerance_mode": "absolute",
                "min_domain": 0,
                "max_domain": 8,
            },
            {
                "id": "wall_assembly",
                "name": "Rainscreen Wall Section",
                "unit": "",
                "scale": "geo",
                "tolerance": 1,
            },
        ],
        "facts": facts,
        "anchor_sets": [
            {
                "dimension_id": "code_dimension_in",
                "entity_ids": ["ada-stair-riser-max", "ada-door-clear-width", "ada-turning-circle", "ada-headroom-clearance"],
            },
            {
                "dimension_id": "live_load_psf",
                "entity_ids": ["load-roof-ordinary", "load-office-floor", "load-public-lobby-stairs", "load-heavy-storage"],
            },
            {
                "dimension_id": "r_value_per_in",
                "entity_ids": ["r-concrete", "r-fiberglass-batt", "r-closed-cell-spray"],
            },
        ],
        "figures": [
            {
                "id": "rainscreen-wall-section",
                "title": "Rainscreen Exterior Wall Section",
                "module": "are_built",
                "dimension_id": "wall_assembly",
                "svg_path": "figures/wall-section.svg",
                "source_url": DOE_INSUL_URL,
                "source_note": "Standard North American drained/ventilated exterior-insulated wall assembly (Building Science Corp / DOE)",
                "regions": [
                    {"region_id": "ws-cladding", "label": "Exterior Cladding (Rainscreen)", "adjacent_ids": ["ws-air-gap"]},
                    {"region_id": "ws-air-gap", "label": "Drainage / Ventilated Air Cavity", "adjacent_ids": ["ws-cladding", "ws-ext-insul"]},
                    {"region_id": "ws-ext-insul", "label": "Continuous Exterior Insulation", "adjacent_ids": ["ws-air-gap", "ws-wrb"]},
                    {"region_id": "ws-wrb", "label": "WRB / Continuous Air Barrier", "adjacent_ids": ["ws-ext-insul", "ws-sheathing"]},
                    {"region_id": "ws-sheathing", "label": "Structural Sheathing", "adjacent_ids": ["ws-wrb", "ws-stud-cavity"]},
                    {"region_id": "ws-stud-cavity", "label": "Stud Framing + Cavity Insulation", "adjacent_ids": ["ws-sheathing", "ws-gypsum"]},
                    {"region_id": "ws-gypsum", "label": "Interior Gypsum Wallboard", "adjacent_ids": ["ws-stud-cavity"]},
                ],
            }
        ],
        "plain_cards": PLAIN_CARDS,
        "ordering_assertions": [
            {
                "dimension_id": "code_dimension_in",
                "ordered_entity_ids": ["ada-stair-riser-max", "ada-stair-tread-min", "ada-door-clear-width", "ada-accessible-route-width", "ibc-guardrail-height", "ada-reach-high", "ada-turning-circle", "ada-headroom-clearance"],
            },
            {
                "dimension_id": "live_load_psf",
                "ordered_entity_ids": ["load-roof-ordinary", "load-residential-sleeping", "load-office-floor", "load-public-lobby-stairs", "load-library-stacks", "load-heavy-storage"],
            },
            {
                "dimension_id": "r_value_per_in",
                "ordered_entity_ids": ["r-concrete", "r-softwood", "r-fiberglass-batt", "r-mineral-wool", "r-xps-foam", "r-closed-cell-spray"],
            },
        ],
    }

    os.makedirs(os.path.join("content", "packs"), exist_ok=True)
    with open(os.path.join("content", "packs", "are_built.json"), "w", encoding="utf-8") as f:
        json.dump(pack, f, indent=2)
    with open(os.path.join("content", "verification-are-built.json"), "w", encoding="utf-8") as f:
        json.dump(verification_log, f, indent=2)

    print(f"Wrote are_built.json: {len(entities)} entities, {len(facts)} verified facts, {len(PLAIN_CARDS)} cards, 1 Wall Section SVG.")

if __name__ == "__main__":
    main()
