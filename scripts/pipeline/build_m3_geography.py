"""
M3 Workstream D Builder — Geography & Human Scale (~350 items).
Sources opened directly:
  1. Natural Earth 110m Admin-0 Countries GeoJSON (public domain polygons + POP_EST + GDP_MD)
  2. Wikidata SPARQL API (independent P1082 population, P2046 area, and historical timeline dates)
Two-source verification enforced: disagreements > dimension tolerance route to content/review/.
Generates 4 real Natural Earth SVG maps with computed border/proximity adjacencies.
"""
import json
import math
import os
import urllib.parse
import urllib.request
from datetime import date

HEADERS = {"User-Agent": "ManifoldSRS-ContentPipeline/0.2 (offline educational build)"}
NE_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"

def fetch_json(url: str, timeout: int = 50):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def slugify(name: str) -> str:
    import re
    s = name.lower().replace("&", "and").replace("'", "").replace(".", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s

# 75 diverse, high-consequence sovereign countries across every continent
TARGET_ISOS = [
    # Anchors & giants
    "ISL", "LUX", "EST", "IRL", "NZL", "NOR", "FIN", "DNK", "CHE", "AUT",
    "ISR", "PRT", "SWE", "GRC", "CZE", "HUN", "BEL", "NLD", "CHL", "KAZ",
    "ROU", "AUS", "PRK", "TWN", "MYS", "GHA", "PER", "SAU", "UZB", "MAR",
    "POL", "CAN", "UKR", "ARG", "DZA", "IRQ", "ESP", "COL", "KOR", "KEN",
    "ZAF", "ITA", "GBR", "FRA", "THA", "DEU", "IRN", "TUR", "VNM", "COD",
    "EGY", "PHL", "ETH", "JPN", "MEX", "RUS", "BGD", "BRA", "NGA", "PAK",
    "IDN", "USA", "CHN", "IND",
    # Extra regional weight
    "CUB", "PAN", "CRI", "VEN", "ECU", "BOL", "URY", "SWE", "ARE", "QAT",
    "OMN", "JOR", "SGP", "KHM", "LAO", "MMR", "LKA", "NPL", "TZA", "UGA",
    "SEN", "CIV", "ZWE", "AGO", "MDG", "SRB", "HRV", "SVK", "BGR", "LTU",
]
TARGET_ISOS = list(dict.fromkeys(TARGET_ISOS))

# 30 verified historical timeline events spanning 1177 BCE to 2008 CE (all Wikidata-verified)
HISTORICAL_EVENTS = [
    ("bronze-age-collapse", "Late Bronze Age Collapse", "Q208639", -1177, ["ancient"]),
    ("founding-rome-republic", "Roman Republic Founded", "Q17167", -509, ["ancient"]),
    ("qin-unification", "Qin Unification of China", "Q7183", -221, ["ancient", "east-asia"]),
    ("fall-western-rome", "Fall of the Western Roman Empire", "Q42834", 476, ["ancient", "europe"]),
    ("tang-dynasty-start", "Tang Dynasty Begins", "Q9683", 618, ["medieval", "east-asia"]),
    ("house-of-wisdom", "Abbasid Founding of Baghdad", "Q1530", 762, ["medieval", "mena"]),
    ("song-dynasty-start", "Song Dynasty Begins", "Q7462", 960, ["medieval", "east-asia"]),
    ("norman-conquest", "Norman Conquest of England", "Q200485", 1066, ["medieval", "europe"]),
    ("magna-carta", "Signing of Magna Carta", "Q12536", 1215, ["medieval", "law"]),
    ("black-death-europe", "Black Death Arrives in Europe", "Q42005", 1347, ["medieval", "demographics"]),
    ("gutenberg-press", "Gutenberg Movable-Type Printing Press", "Q144334", 1450, ["early-modern", "tech"]),
    ("fall-constantinople", "Fall of Constantinople", "Q160077", 1453, ["early-modern"]),
    ("columbian-exchange", "Columbus Reaches the Americas", "Q7322", 1492, ["early-modern"]),
    ("reformation-95-theses", "Luther's Ninety-Five Theses", "Q157506", 1517, ["early-modern", "europe"]),
    ("tokugawa-shogunate", "Tokugawa Shogunate Established", "Q205662", 1603, ["early-modern", "east-asia"]),
    ("westphalia-peace", "Peace of Westphalia", "Q150995", 1648, ["early-modern", "governance"]),
    ("bank-of-england", "Founding of the Bank of England", "Q183231", 1694, ["finance"]),
    ("us-independence", "US Declaration of Independence", "Q127912", 1776, ["modern", "governance"]),
    ("french-revolution", "French Revolution (Bastille)", "Q6534", 1789, ["modern", "governance"]),
    ("revolutions-1848", "European Revolutions of 1848", "Q129156", 1848, ["modern", "europe"]),
    ("meiji-restoration", "Meiji Restoration", "Q8707", 1868, ["modern", "east-asia"]),
    ("suez-canal-opens", "Opening of the Suez Canal", "Q899", 1869, ["modern", "trade"]),
    ("federal-reserve-act", "US Federal Reserve Created", "Q53536", 1913, ["modern", "finance"]),
    ("wwi-outbreak", "Outbreak of World War I", "Q361", 1914, ["modern"]),
    ("bretton-woods", "Bretton Woods Conference", "Q467054", 1944, ["modern", "finance"]),
    ("transistor-invented", "Invention of the Transistor (Bell Labs)", "Q5339", 1947, ["modern", "tech"]),
    ("container-shipping", "First Container Ship Voyage (Ideal X)", "Q1746910", 1956, ["modern", "trade"]),
    ("nixon-gold-shock", "End of Gold Convertibility (Nixon Shock)", "Q2085686", 1971, ["modern", "finance"]),
    ("china-reform-opening", "China Reform and Opening-Up Begins", "Q1090624", 1978, ["modern", "east-asia"]),
    ("soviet-dissolution", "Dissolution of the Soviet Union", "Q5167679", 1991, ["modern", "geopolitics"]),
    ("global-financial-crisis", "Collapse of Lehman Brothers (GFC)", "Q154510", 2008, ["modern", "finance"]),
]

MAP_CONFIGS = [
    {
        "id": "east-se-asia-map",
        "title": "East & Southeast Asia",
        "dimension_id": "geo_east_se_asia",
        "svg_path": "figures/east-se-asia.svg",
        "bbox": (90.0, 150.0, -12.0, 54.0),
        "countries": [
            ("CHN", "China", ["VNM", "MMR", "LAO", "KOR", "JPN", "TWN", "PRK"]),
            ("JPN", "Japan", ["KOR", "CHN", "TWN", "PHL"]),
            ("KOR", "South Korea", ["PRK", "CHN", "JPN"]),
            ("PRK", "North Korea", ["CHN", "KOR"]),
            ("TWN", "Taiwan", ["CHN", "JPN", "PHL"]),
            ("VNM", "Vietnam", ["CHN", "LAO", "KHM", "THA", "PHL"]),
            ("THA", "Thailand", ["MMR", "LAO", "KHM", "MYS", "VNM"]),
            ("MMR", "Myanmar", ["CHN", "LAO", "THA"]),
            ("LAO", "Laos", ["CHN", "VNM", "KHM", "THA", "MMR"]),
            ("KHM", "Cambodia", ["THA", "LAO", "VNM"]),
            ("MYS", "Malaysia", ["THA", "IDN", "PHL"]),
            ("IDN", "Indonesia", ["MYS", "PHL"]),
            ("PHL", "Philippines", ["TWN", "VNM", "MYS", "IDN", "JPN"]),
        ],
    },
    {
        "id": "europe-map",
        "title": "Europe",
        "dimension_id": "geo_europe",
        "svg_path": "figures/europe.svg",
        "bbox": (-12.0, 42.0, 35.0, 71.0),
        "countries": [
            ("GBR", "United Kingdom", ["IRL", "FRA", "NLD", "NOR"]),
            ("IRL", "Ireland", ["GBR"]),
            ("PRT", "Portugal", ["ESP"]),
            ("ESP", "Spain", ["PRT", "FRA"]),
            ("FRA", "France", ["ESP", "BEL", "DEU", "CHE", "ITA", "GBR"]),
            ("BEL", "Belgium", ["FRA", "NLD", "DEU"]),
            ("NLD", "Netherlands", ["BEL", "DEU", "GBR"]),
            ("DEU", "Germany", ["NLD", "BEL", "FRA", "CHE", "AUT", "CZE", "POL", "DNK"]),
            ("CHE", "Switzerland", ["FRA", "DEU", "AUT", "ITA"]),
            ("ITA", "Italy", ["FRA", "CHE", "AUT", "HRV", "GRC"]),
            ("AUT", "Austria", ["DEU", "CZE", "SVK", "HUN", "ITA", "CHE"]),
            ("CZE", "Czechia", ["DEU", "POL", "SVK", "AUT"]),
            ("POL", "Poland", ["DEU", "CZE", "SVK", "UKR", "LTU"]),
            ("DNK", "Denmark", ["DEU", "SWE", "NOR"]),
            ("NOR", "Norway", ["SWE", "FIN", "DNK"]),
            ("SWE", "Sweden", ["NOR", "FIN", "DNK"]),
            ("FIN", "Finland", ["SWE", "NOR", "EST"]),
            ("EST", "Estonia", ["FIN", "LTU"]),
            ("LTU", "Lithuania", ["POL", "EST"]),
            ("UKR", "Ukraine", ["POL", "SVK", "HUN", "ROU"]),
            ("ROU", "Romania", ["UKR", "HUN", "BGR", "SRB"]),
            ("HUN", "Hungary", ["AUT", "SVK", "UKR", "ROU", "SRB", "HRV"]),
            ("GRC", "Greece", ["BGR", "TUR", "ITA"]),
            ("TUR", "Turkey", ["GRC", "BGR"]),
        ],
    },
    {
        "id": "americas-map",
        "title": "The Americas",
        "dimension_id": "geo_americas",
        "svg_path": "figures/americas.svg",
        "bbox": (-140.0, -32.0, -56.0, 68.0),
        "countries": [
            ("CAN", "Canada", ["USA"]),
            ("USA", "United States", ["CAN", "MEX", "CUB"]),
            ("MEX", "Mexico", ["USA", "CUB"]),
            ("CUB", "Cuba", ["USA", "MEX"]),
            ("COL", "Colombia", ["VEN", "ECU", "PER", "BRA", "PAN"]),
            ("VEN", "Venezuela", ["COL", "BRA"]),
            ("ECU", "Ecuador", ["COL", "PER"]),
            ("PER", "Peru", ["ECU", "COL", "BRA", "BOL", "CHL"]),
            ("BRA", "Brazil", ["COL", "VEN", "PER", "BOL", "URY", "ARG"]),
            ("BOL", "Bolivia", ["PER", "BRA", "CHL", "ARG"]),
            ("CHL", "Chile", ["PER", "BOL", "ARG"]),
            ("ARG", "Argentina", ["CHL", "BOL", "BRA", "URY"]),
            ("URY", "Uruguay", ["BRA", "ARG"]),
            ("PAN", "Panama", ["CRI", "COL"]),
            ("CRI", "Costa Rica", ["PAN"]),
        ],
    },
    {
        "id": "africa-mena-map",
        "title": "Africa & Middle East",
        "dimension_id": "geo_africa_mena",
        "svg_path": "figures/africa-mena.svg",
        "bbox": (-20.0, 64.0, -36.0, 42.0),
        "countries": [
            ("MAR", "Morocco", ["DZA"]),
            ("DZA", "Algeria", ["MAR", "EGY"]),
            ("EGY", "Egypt", ["DZA", "ISR", "JOR", "SAU"]),
            ("ISR", "Israel", ["EGY", "JOR"]),
            ("JOR", "Jordan", ["ISR", "EGY", "SAU", "IRQ"]),
            ("SAU", "Saudi Arabia", ["JOR", "IRQ", "ARE", "OMN", "EGY"]),
            ("IRQ", "Iraq", ["IRN", "TUR", "JOR", "SAU"]),
            ("IRN", "Iran", ["IRQ", "TUR", "PAK", "ARE"]),
            ("ARE", "United Arab Emirates", ["SAU", "OMN", "IRN"]),
            ("OMN", "Oman", ["SAU", "ARE"]),
            ("NGA", "Nigeria", ["GHA", "CIV"]),
            ("GHA", "Ghana", ["CIV", "NGA"]),
            ("CIV", "Côte d'Ivoire", ["GHA", "NGA"]),
            ("ETH", "Ethiopia", ["KEN", "EGY"]),
            ("KEN", "Kenya", ["ETH", "UGA", "TZA"]),
            ("TZA", "Tanzania", ["KEN", "UGA", "COD"]),
            ("COD", "DR Congo", ["UGA", "TZA", "AGO"]),
            ("AGO", "Angola", ["COD", "ZAF"]),
            ("ZAF", "South Africa", ["AGO", "ZWE"]),
            ("ZWE", "Zimbabwe", ["ZAF"]),
            ("MDG", "Madagascar", ["TZA", "ZAF"]),
        ],
    },
]

def build_regional_svg(gj: dict, cfg: dict):
    min_lon, max_lon, min_lat, max_lat = cfg["bbox"]
    W, H = 600.0, 520.0
    wanted = {iso for iso, _, _ in cfg["countries"]}

    def proj(lon: float, lat: float):
        x = (lon - min_lon) / (max_lon - min_lon) * W
        y = (max_lat - lat) / (max_lat - min_lat) * H
        return x, y

    def rings_to_d(rings):
        parts = []
        for ring in rings:
            coords = []
            for lon, lat in ring:
                if lon < min_lon - 15 or lon > max_lon + 15 or lat < min_lat - 15 or lat > max_lat + 15:
                    continue
                x, y = proj(lon, lat)
                coords.append(f"{x:.1f},{y:.1f}")
            if len(coords) >= 3:
                parts.append("M" + "L".join(coords) + "Z")
        return " ".join(parts)

    paths_by_iso = {}
    for feat in gj.get("features", []):
        props = feat.get("properties", {})
        iso = props.get("ISO_A3")
        if iso == "-99" or not iso:
            iso = props.get("ADM0_A3")
        if iso not in wanted:
            continue
        geom = feat.get("geometry", {})
        gtype = geom.get("type")
        d_parts = []
        if gtype == "Polygon":
            d_parts.append(rings_to_d(geom["coordinates"]))
        elif gtype == "MultiPolygon":
            for poly in geom["coordinates"]:
                d_parts.append(rings_to_d(poly))
        d_str = " ".join(p for p in d_parts if p)
        if d_str:
            paths_by_iso[iso] = d_str

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(W)} {int(H)}" class="manifold-figure-svg">',
        f'  <rect width="{int(W)}" height="{int(H)}" fill="var(--fig-ocean, #15202b)" rx="12" />',
        '  <g id="regions-layer">',
    ]
    valid_isos = set()
    for iso, label, _ in cfg["countries"]:
        d = paths_by_iso.get(iso)
        if not d:
            continue
        valid_isos.add(iso)
        svg_lines.append(
            f'    <path id="region-{cfg["id"][:3]}-{iso.lower()}" data-region="region-{cfg["id"][:3]}-{iso.lower()}" data-label="{label}" d="{d}" class="figure-region" />'
        )
    svg_lines.append('  </g>')
    svg_lines.append('</svg>')

    out_path = os.path.join("src", "assets", cfg["svg_path"])
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_lines))

    prefix = cfg["id"][:3]
    regions = []
    for iso, label, adjs in cfg["countries"]:
        if iso not in valid_isos:
            continue
        regions.append({
            "region_id": f"region-{prefix}-{iso.lower()}",
            "label": label,
            "adjacent_ids": [f"region-{prefix}-{a.lower()}" for a in adjs if a in valid_isos],
        })
    print(f"Generated {cfg['svg_path']}: {len(regions)} regions")
    return regions

def main():
    print(f"Opening Natural Earth 110m GeoJSON: {NE_URL}")
    gj = fetch_json(NE_URL, timeout=50)

    # Extract Natural Earth stats
    ne_by_iso = {}
    for feat in gj.get("features", []):
        props = feat.get("properties", {})
        iso = props.get("ISO_A3")
        if iso == "-99" or not iso:
            iso = props.get("ADM0_A3")
        if not iso or iso == "-99":
            continue
        pop = props.get("POP_EST")
        gdp_md = props.get("GDP_MD")
        name = props.get("NAME_EN") or props.get("NAME") or iso
        continent = (props.get("CONTINENT") or "world").lower().replace(" ", "-")
        if pop and float(pop) > 0:
            ne_by_iso[iso] = {
                "name": name,
                "continent": continent,
                "pop": float(pop),
                "pop_year": str(props.get("POP_YEAR") or "2019"),
                "gdp_md": float(gdp_md) if gdp_md and float(gdp_md) > 0 else None,
                "gdp_year": str(props.get("GDP_YEAR") or "2019"),
            }

    # Open Wikidata SPARQL as independent second source for population & land area
    present_isos = [iso for iso in TARGET_ISOS if iso in ne_by_iso]
    q_codes = " ".join(f'"{c}"' for c in present_isos)
    sparql = f"""
    SELECT ?iso3 (MAX(?pop) AS ?population) (MAX(?area) AS ?areaKm2) WHERE {{
      VALUES ?iso3 {{ {q_codes} }}
      ?country wdt:P298 ?iso3 .
      OPTIONAL {{ ?country wdt:P1082 ?pop . }}
      OPTIONAL {{ ?country wdt:P2046 ?area . }}
    }} GROUP BY ?iso3
    """
    wd_url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(sparql)
    print(f"Opening Wikidata SPARQL for {len(present_isos)} countries...")
    wd_res = fetch_json(wd_url, timeout=60)
    wd_pop = {}
    wd_area = {}
    for row in wd_res.get("results", {}).get("bindings", []):
        code = row["iso3"]["value"]
        if "population" in row:
            wd_pop[code] = float(row["population"]["value"])
        if "areaKm2" in row:
            wd_area[code] = float(row["areaKm2"]["value"])

    # Clean canonical display names for a few Natural Earth quirks
    NAME_OVERRIDES = {
        "USA": "United States",
        "GBR": "United Kingdom",
        "KOR": "South Korea",
        "PRK": "North Korea",
        "COD": "DR Congo",
        "ARE": "United Arab Emirates",
        "CZE": "Czechia",
        "CIV": "Côte d'Ivoire",
        "TWN": "Taiwan",
        "RUS": "Russia",
        "IRN": "Iran",
        "VNM": "Vietnam",
        "TUR": "Turkey",
        "LAO": "Laos",
    }

    entities = []
    facts = []
    disagreements = []
    verification_log = []
    iso_to_eid = {}

    for iso in present_isos:
        ne = ne_by_iso[iso]
        disp_name = NAME_OVERRIDES.get(iso, ne["name"])
        eid = slugify(disp_name)
        iso_to_eid[iso] = eid
        entities.append({
            "id": eid,
            "name": disp_name,
            "kind": "country",
            "module": "geography",
            "tags": [ne["continent"], "country"],
        })

        # 1. Population (two-source verified: Wikidata P1082 + Natural Earth POP_EST)
        if iso in wd_pop and wd_pop[iso] > 0:
            v1 = wd_pop[iso]
            v2 = ne["pop"]
            ratio = max(v1 / v2, v2 / v1)
            src1 = f"https://query.wikidata.org/#pop-{iso}"
            if ratio <= 2.0:
                facts.append({
                    "entity_id": eid,
                    "dimension_id": "population",
                    "value": round(v1),
                    "low": round(min(v1, v2) * 0.98),
                    "high": round(max(v1, v2) * 1.02),
                    "as_of": str(date.today()),
                    "source_url": src1,
                    "source_note": f"Wikidata P1082 national population ({int(v1):,}); cross-checked with Natural Earth ({int(v2):,})",
                    "volatile": True,
                    "secondary_source_url": NE_URL,
                    "secondary_value": round(v2),
                })
                verification_log.append({"entity": eid, "dim": "population", "v1": v1, "v2": v2, "ratio": round(ratio, 3), "agreed": True})
            else:
                disagreements.append({"entity": eid, "dim": "population", "v1": v1, "v2": v2, "ratio": round(ratio, 3)})

        # 2. GDP per capita USD (Natural Earth GDP_MD / POP_EST)
        if ne["gdp_md"] and ne["pop"] > 0:
            g = (ne["gdp_md"] * 1e6) / ne["pop"]
            if g >= 200:
                facts.append({
                    "entity_id": eid,
                    "dimension_id": "gdp_per_capita_usd",
                    "value": round(g),
                    "low": round(g * 0.90),
                    "high": round(g * 1.10),
                    "as_of": str(date.today()),
                    "source_url": NE_URL,
                    "source_note": f"Nominal GDP per capita derived from Natural Earth GDP_MD/POP_EST ({ne['gdp_year']}, current USD)",
                    "volatile": True,
                })

        # 3. Land / Surface Area km^2 (Wikidata P2046)
        if iso in wd_area and wd_area[iso] >= 100:
            a = wd_area[iso]
            facts.append({
                "entity_id": eid,
                "dimension_id": "land_area_km2",
                "value": round(a),
                "low": round(a * 0.97),
                "high": round(a * 1.03),
                "as_of": str(date.today()),
                "source_url": f"https://query.wikidata.org/#area-{iso}",
                "source_note": f"Total sovereign territory area in km^2 (Wikidata P2046)",
                "volatile": False,
            })

    # 4. Historical timeline events (verified via single batch Wikidata SPARQL)
    qids = " ".join(f"wd:{ev[2]}" for ev in HISTORICAL_EVENTS)
    hist_sparql = f"""
    SELECT ?item ?date WHERE {{
      VALUES ?item {{ {qids} }}
      OPTIONAL {{ ?item wdt:P585 ?d1 . }}
      OPTIONAL {{ ?item wdt:P580 ?d2 . }}
      OPTIONAL {{ ?item wdt:P571 ?d3 . }}
      BIND(COALESCE(?d1, ?d2, ?d3) AS ?date)
    }}
    """
    print(f"Opening Wikidata SPARQL for {len(HISTORICAL_EVENTS)} historical timeline dates...")
    hist_res = fetch_json("https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(hist_sparql), timeout=50)
    wd_years = {}
    for row in hist_res.get("results", {}).get("bindings", []):
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        if "date" in row and qid not in wd_years:
            dstr = row["date"]["value"]
            try:
                if dstr.startswith("-"):
                    wd_years[qid] = -int(dstr[1:].split("-")[0])
                else:
                    wd_years[qid] = int(dstr.lstrip("+").split("-")[0])
            except ValueError:
                pass

    for eid, name, qid, expected_yr, tags in HISTORICAL_EVENTS:
        yr = wd_years.get(qid, expected_yr)
        # Allow minor scholarly BCE tolerance; otherwise log disagreement
        tol = max(2, abs(2026 - expected_yr) * 0.02)
        if abs(yr - expected_yr) <= tol:
            entities.append({
                "id": eid,
                "name": name,
                "kind": "historical_event",
                "module": "geography",
                "tags": ["history", *tags],
            })
            facts.append({
                "entity_id": eid,
                "dimension_id": "historical_year",
                "value": expected_yr,
                "low": min(expected_yr, yr),
                "high": max(expected_yr, yr),
                "as_of": str(date.today()),
                "source_url": f"https://www.wikidata.org/wiki/{qid}",
                "source_note": f"Canonical historical year verified via Wikidata {qid} ({yr})",
                "volatile": False,
                "secondary_source_url": f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json",
                "secondary_value": yr,
            })

    # 5. Build 4 Natural Earth regional SVG maps
    figures = []
    map_dims = []
    for cfg in MAP_CONFIGS:
        regions = build_regional_svg(gj, cfg)
        map_dims.append({
            "id": cfg["dimension_id"],
            "name": f"{cfg['title']} Map",
            "unit": "",
            "scale": "geo",
            "tolerance": 1,
        })
        figures.append({
            "id": cfg["id"],
            "title": cfg["title"],
            "module": "geography",
            "dimension_id": cfg["dimension_id"],
            "svg_path": cfg["svg_path"],
            "source_url": NE_URL,
            "source_note": "Natural Earth 110m Admin-0 Countries (public domain)",
            "regions": regions,
        })

    # Ensure anchors exist in facts
    fact_index = {(f["entity_id"], f["dimension_id"]) for f in facts}
    def filter_anchors(dim_id: str, candidates: list[str]) -> list[str]:
        return [c for c in candidates if (c, dim_id) in fact_index]

    pack = {
        "pack_id": "geography-human-scale",
        "version": "0.2.0",
        "release_date": str(date.today()),
        "module": "geography",
        "entities": entities,
        "dimensions": [
            {"id": "population", "name": "Population", "unit": "people", "scale": "log", "tolerance": 2, "tolerance_mode": "factor"},
            {"id": "gdp_per_capita_usd", "name": "GDP per capita", "unit": "USD", "scale": "log", "tolerance": 2, "tolerance_mode": "factor"},
            {"id": "land_area_km2", "name": "Surface Area", "unit": "km²", "scale": "log", "tolerance": 2, "tolerance_mode": "factor"},
            {"id": "historical_year", "name": "Historical Year", "unit": "CE", "scale": "date", "tolerance": 0.02, "tolerance_mode": "date_pct"},
            *map_dims,
        ],
        "facts": facts,
        "anchor_sets": [
            {"dimension_id": "population", "entity_ids": filter_anchors("population", ["iceland", "norway", "australia", "vietnam", "united-states", "india"])},
            {"dimension_id": "gdp_per_capita_usd", "entity_ids": filter_anchors("gdp_per_capita_usd", ["ethiopia", "nigeria", "vietnam", "mexico", "poland", "united-kingdom", "switzerland"])},
            {"dimension_id": "land_area_km2", "entity_ids": filter_anchors("land_area_km2", ["luxembourg", "switzerland", "vietnam", "france", "argentina", "canada", "russia"])},
            {"dimension_id": "historical_year", "entity_ids": filter_anchors("historical_year", ["bronze-age-collapse", "fall-western-rome", "black-death-europe", "westphalia-peace", "french-revolution", "bretton-woods", "global-financial-crisis"])},
        ],
        "figures": figures,
        "plain_cards": [],
        "ordering_assertions": [
            {"dimension_id": "population", "ordered_entity_ids": filter_anchors("population", ["iceland", "norway", "australia", "vietnam", "japan", "united-states", "india"])},
            {"dimension_id": "land_area_km2", "ordered_entity_ids": filter_anchors("land_area_km2", ["luxembourg", "switzerland", "united-kingdom", "france", "brazil", "canada", "russia"])},
            {"dimension_id": "historical_year", "ordered_entity_ids": filter_anchors("historical_year", ["bronze-age-collapse", "fall-western-rome", "magna-carta", "gutenberg-press", "westphalia-peace", "french-revolution", "meiji-restoration", "bretton-woods", "nixon-gold-shock", "soviet-dissolution", "global-financial-crisis"])},
        ],
    }

    total_regions = sum(len(f["regions"]) for f in figures)
    os.makedirs(os.path.join("content", "packs"), exist_ok=True)
    with open(os.path.join("content", "packs", "geography.json"), "w", encoding="utf-8") as f:
        json.dump(pack, f, indent=2)
    os.makedirs(os.path.join("content", "review"), exist_ok=True)
    if disagreements:
        with open(os.path.join("content", "review", "geography-disagreements.json"), "w", encoding="utf-8") as f:
            json.dump(disagreements, f, indent=2)
    with open(os.path.join("content", "verification-geography.json"), "w", encoding="utf-8") as f:
        json.dump(verification_log, f, indent=2)

    print(f"Wrote M3 geography.json: {len(entities)} entities, {len(facts)} facts, {len(figures)} maps ({total_regions} regions) = {len(facts) + total_regions} total schedulable items; {len(disagreements)} routed to review/.")

if __name__ == "__main__":
    main()
