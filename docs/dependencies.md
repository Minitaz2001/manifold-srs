# Dependency Justifications

Per Design Doc v0.1 ("No new dependency without a one-line justification"):

## Runtime Dependencies
- `react`, `react-dom`: Component rendering for the three one-thumb review widgets and minimal settings/telemetry views.
- `dexie`: Ergonomic IndexedDB wrapper specified in Section 2 (Requirements #4) for user state (`item_state`, `review_log`, `probe_queue`, `inbox`, `settings`).
- `ts-fsrs` (`5.4.2`): Specified FSRS scheduler in Section 4; pinned to v5.4.2 because it is pure synchronous TypeScript with zero runtime dependencies and zero `fetch(`/WASM calls.

## Development & Validation Dependencies
- `typescript`, `@types/*`: Static type safety across content contracts, grading math, and FSRS state.
- `vite`, `@vitejs/plugin-react`: Static production bundling with inline asset/JSON/SVG imports so runtime executes zero `fetch(` calls.
- `vite-plugin-pwa`: Generates the Web App Manifest and Workbox precaching service worker for offline-first iPhone home-screen delivery.
- `vitest`, `fake-indexeddb`: Fast unit tests for pure grading/scheduling/hygiene functions and real IndexedDB backup round-trip and log-replay verification.
- `ajv`, `ajv-formats`: JSON Schema Draft-07/2020 validation with URI and date format checking for the M0 content validator CLI.
- `tsx`: Executes TypeScript CLI scripts (`validate-content.ts`, `check-bundle.ts`) without a separate build step.
