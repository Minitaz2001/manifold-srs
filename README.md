# Manifold SRS

Offline-first spaced repetition on continuous manifolds for iPhone (installable PWA).

## Quick start

```bash
npm install
npm run ci          # validate all content packs -> run 42 unit/integration tests -> build -> check zero runtime fetch(
npm run dev         # local dev server
npm run preview     # preview production PWA build (with service worker)
```

## Content Launch (M3 — 882 items)

- `geography.json` — 376 items (303 facts across 92 countries & 31 historical dates + 4 Natural Earth SVG maps with 73 regions).
- `physics.json` — 216 items (179 facts across 10 quantitative ladders + 20 scaling-law cards + 2 SVGs with 17 regions).
- `are_built.json` — 146 items aimed at ARE 5.0 PjM / CE / PA (+ shared PcM AIA contracts): 53 code/load/soil/practice facts + 69 recall cards + 3 architectural SVGs (24 regions).
- `natural_world.json` — 144 NYC & Northeast visual cards with locally bundled openly licensed Wikimedia Commons photographs and per-image attribution.

### What "verified" means here (2026-11-19 audit)

The original pipeline's "two-source" check only confirmed each cited URL returned >200 characters; secondary values were hand-typed copies and many secondary URLs were unrelated. That claim is withdrawn and the old `verification-*.json` logs were deleted. Current state:

- **Population & GDP per capita (181 of 184):** re-sourced from the World Bank API, most recent year (`scripts/pipeline/refresh_worldbank.py`). Taiwan (both) and North Korea GDP are not covered and carry agent-audited values.
- **Everything else (facts + recall cards, 624 items audited):** independent LLM fact-check, one pass per item, mostly from model knowledge with web lookups where uncertain. Results in `content/verification/agent-audit.json`: 541 ok, 46 corrected, 37 unsure (kept). Applied by `scripts/pipeline/apply_agent_audit.py`. This is a careful second opinion, not a second primary source.
- **Natural-world photo cards:** not audited (image ↔ species match unchecked).

## Architecture

- `schemas/` — Frozen M0 JSON Schema Draft-07 contracts (`entity`, `dimension`, `fact`, `anchor_set`, `figure`, `plain_card`, `pack`).
- `scripts/validate-content.ts` — Content validator CLI (schema, `source_url` enforcement, near-duplicate check, monotonicity, ≥80% anchor bracketing, 1.2× log anti-collision, SVG region IDs, media attribution).
- `scripts/check-bundle.ts` — Post-build CI gate verifying zero `fetch(` or `XMLHttpRequest` calls in built bundles outside the service worker.
- `scripts/pipeline/` — Build-time content fetchers, World Bank refresh, and the agent-audit applier (Natural Earth, Wikidata, NIST, DOE AFDC, USGS, EIA, 2010 ADA Standards, Wikimedia Commons).
- `src/platform/` — Thin browser/iOS wrapper abstraction (storage persistence, Share Sheet JSON export, haptics stub, monotonic clock).
- `src/core/` — Pure table-driven grading (`grading.ts`), deterministic `ts-fsrs` scheduling + `review_log` replay (`scheduler.ts`), interleaving & ratio-probe queue builder (`queue.ts`), atomic backup (`backup.ts`), calibration & latency telemetry (`telemetry.ts`).
- `src/widgets/` — Strictly three review widgets (`RulerWidget`, `OccludeWidget`, `PlainCardWidget`) plus the unscored `RatioProbeWidget` detector.
- `content/packs/` — Read-only versioned launch packs (Geography & Human Scale, Physical & Quantitative Ladders, Natural World Northeast, Built Environment ARE).

## Deployment (iPhone PWA)

Push to GitHub with Pages enabled (`.github/workflows/deploy.yml` runs `npm run ci` and deploys `dist/`), open once in Safari on iPhone, tap **Share → Add to Home Screen**. Works fully offline thereafter.
