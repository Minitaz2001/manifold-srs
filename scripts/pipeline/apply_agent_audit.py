"""
Apply the agent fact-check (content/verification/results/b*.json) to the launch packs.

Policy:
  ok      -> keep; secondary source replaced by the agent's evidence_url if it checked one,
             otherwise the old (unrelated) secondary_source_url/secondary_value is removed.
  wrong   -> if a corrected_value AND evidence_url were given: fix value (band collapses to the
             corrected value; dimension tolerance still applies), source_url := evidence_url.
             otherwise: drop the item.
  unsure  -> keep, unchanged except the fake secondary is removed.
Writes content/verification/agent-audit.json (every verdict) and prints a summary.
"""
import glob
import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PACKS = {"geography": "geography.json", "physics": "physics.json", "are_built": "are_built.json"}

results = {}
for p in sorted(glob.glob(os.path.join(ROOT, "content/verification/results/b*.json"))):
    for r in json.load(open(p, encoding="utf8")):
        results[r["key"]] = r

expected = []
for p in sorted(glob.glob(os.path.join(ROOT, "content/verification/batches/b*.json"))):
    expected += [i["key"] for i in json.load(open(p, encoding="utf8"))]
missing = [k for k in expected if k not in results]
if missing:
    raise SystemExit(f"{len(missing)} items have no verdict, e.g. {missing[:5]}")

stats = Counter()
changes = []
for pack, fn in PACKS.items():
    path = os.path.join(ROOT, "content/packs", fn)
    d = json.load(open(path, encoding="utf8"))
    kept_facts = []
    for f in d["facts"]:
        key = f"{pack}|fact|{f['entity_id']}|{f['dimension_id']}"
        r = results[key]
        v = r["verdict"]
        f.pop("secondary_value", None)
        f.pop("secondary_source_url", None)
        ev = r.get("evidence_url")
        if v == "wrong":
            cv = r.get("corrected_value")
            if isinstance(cv, (int, float)) and not isinstance(cv, bool):
                changes.append(f"FIX  {key}: {f['value']} -> {cv} ({r.get('note')})")
                f["value"] = cv
                if not (f["low"] <= cv <= f["high"]):
                    f["low"] = f["high"] = cv
                if ev:
                    f["source_url"] = ev
                f["source_note"] = (f.get("source_note") or "") + f" [agent-corrected: {r.get('note')}]"
                stats["fixed"] += 1
            else:
                changes.append(f"DROP {key}: {r.get('note')}")
                stats["dropped"] += 1
                continue
        else:
            if ev and ev != f.get("source_url"):
                f["secondary_source_url"] = ev
                f["secondary_value"] = f["value"]
            stats[v] += 1
        kept_facts.append(f)
    d["facts"] = kept_facts

    kept_cards = []
    for c in d.get("plain_cards", []):
        r = results[f"{pack}|card|{c['id']}"]
        if r["verdict"] == "wrong":
            cv = r.get("corrected_value")
            if isinstance(cv, str) and cv.strip():
                changes.append(f"FIX  card {c['id']}: {r.get('note')}")
                c["back"] = cv
                if r.get("evidence_url"):
                    c["source_url"] = r["evidence_url"]
                stats["fixed"] += 1
            else:
                changes.append(f"DROP card {c['id']}: {r.get('note')}")
                stats["dropped"] += 1
                continue
        else:
            stats[r["verdict"]] += 1
        kept_cards.append(c)
    d["plain_cards"] = kept_cards

    # keep anchor sets / orderings consistent with surviving facts
    live = {(f["entity_id"], f["dimension_id"]) for f in d["facts"]}
    for a in d.get("anchor_sets", []):
        a["entity_ids"] = [e for e in a["entity_ids"] if (e, a["dimension_id"]) in live]
    for o in d.get("ordering_assertions", []):
        o["ordered_entity_ids"] = [e for e in o["ordered_entity_ids"] if (e, o["dimension_id"]) in live]
    used = {f["entity_id"] for f in d["facts"]} | {e for fig in d.get("figures", []) for e in [fig.get("entity_id")] if e}
    json.dump(d, open(path, "w", encoding="utf8"), ensure_ascii=False, indent=2)

json.dump(list(results.values()), open(os.path.join(ROOT, "content/verification/agent-audit.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
print(dict(stats))
print("\n".join(changes))
