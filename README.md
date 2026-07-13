# OnPoint.

Journey planner for German train routes with historical transfer reliability, expected delay simulation, and Plan-B route estimates.

## Project Layout

- `filedforBahnprojekt/backend.py` - Flask API and route scoring.
- `filedforBahnprojekt/scrape_train_data.py` - station-board scraper for historical MySQL data.
- `filedforBahnprojekt/connection_model.py` - statistical transfer model.
- `filedforBahnprojekt/my-app/` - SvelteKit frontend.

## DB API runtime

DB currently blocks the TLS/network fingerprint used by Node for the Vendo
endpoints. Install the frontend dependencies with `npm install`; they include a
platform-specific Bun runtime that the Python backend and scraper select when
`NODE_EXECUTABLE=auto` (the default). Bun's npm package supports Linux ARM64 for
64-bit Raspberry Pi installations. Set `NODE_EXECUTABLE` to an explicit binary
path only when an override is required.

Long routes analyze six complete alternatives by default (`MAX_ROUTE_RESULTS`).
Every transfer still receives an exact Plan-B lookup; these lookups run with
bounded parallelism (`FALLBACK_ROUTE_WORKERS`, default: `3`) and identical
requests are reused within the analysis.

