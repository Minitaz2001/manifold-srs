"""
Re-source geography population + GDP per capita from the World Bank API (most recent non-empty
year per country). Replaces the stale Natural Earth 2019 values. Countries the World Bank does
not cover (e.g. Taiwan, North Korea GDP) keep their agent-audited value and are listed.
Run after apply_agent_audit.py.
"""
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_geography import COUNTRIES  # noqa: E402

INDICATORS = {"population": ("SP.POP.TOTL", 0.03), "gdp_per_capita_usd": ("NY.GDP.PCAP.CD", 0.10)}


def fetch(indicator, isos):
    out = {}
    for i in range(0, len(isos), 8):
        url = (f"https://api.worldbank.org/v2/country/{';'.join(isos[i:i+8])}/indicator/{indicator}"
               f"?format=json&mrnev=1&per_page=100")
        for attempt in range(4):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "content-pipeline"}), timeout=90) as r:
                    data = json.loads(r.read().decode("utf8"))
                break
            except Exception as exc:
                print("  retry", attempt + 1, indicator, i, exc)
        else:
            continue
        for row in (data[1] or []) if len(data) > 1 else []:
            if row.get("value") is not None:
                out[row["countryiso3code"]] = (float(row["value"]), row["date"])
    return out


iso_of = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "country_iso3.json")))
path = os.path.join(ROOT, "content/packs/geography.json")
d = json.load(open(path, encoding="utf8"))
uncovered = []
for dim, (ind, band) in INDICATORS.items():
    got = fetch(ind, sorted(set(iso_of.values())))
    for f in d["facts"]:
        if f["dimension_id"] != dim:
            continue
        iso = iso_of.get(f["entity_id"])
        if iso not in got:
            uncovered.append(f"{f['entity_id']}/{dim}")
            continue
        v, year = got[iso]
        v = round(v) if dim == "population" else round(v)
        f.update({
            "value": v, "low": round(v * (1 - band)), "high": round(v * (1 + band)),
            "source_url": f"https://api.worldbank.org/v2/country/{iso}/indicator/{ind}?format=json&mrnev=1",
            "source_note": f"World Bank {ind}, {year}" + (" (current USD)" if dim != "population" else ""),
        })
        f.pop("secondary_source_url", None)
        f.pop("secondary_value", None)
json.dump(d, open(path, "w", encoding="utf8"), ensure_ascii=False, indent=2)
print("not covered by World Bank (kept audited value):", uncovered)
