# OnPoint.

Journey planner for German train routes with historical transfer reliability, expected delay simulation, and Plan-B route estimates.

## Project Layout

- `filedforBahnprojekt/backend.py` - Flask API and route scoring.
- `filedforBahnprojekt/scrape_train_data.py` - station-board scraper for historical MySQL data.
- `filedforBahnprojekt/migrate_train_db.py` - idempotent MySQL migration for compact event UPSERTs.
- `filedforBahnprojekt/scrape_stations.txt` - Raspberry Pi scrape station set.
- `filedforBahnprojekt/compact_train_db.py` - optional one-time removal of old duplicate snapshots.
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
requests are reused within the analysis. All Plan-B lookups of one analysis
share a single Bun process so the DB client and station index are loaded once.

The Flask reloader is disabled by default (`FLASK_DEBUG=false`). Production
deployments should run `backend:app` through Gunicorn instead of Flask's
development server.

## Historical event storage

Each arrival or departure is identified by:

`event type + internal station id + DB trip id + planned date/time`

The planned date and time keep repeated runs of the same line separate. A train
that serves the same route several times on one day therefore creates several
events. Repeated observations of the same event update its actual time, delay,
and cancellation state instead of appending duplicate snapshots.

The scraper keeps the latest/final historical delay needed by the connection
model. It does not retain every intermediate prediction for one event.

DB Web sometimes removes realtime information from old trains and returns only
their planned times. Each observation therefore carries a `realtime_known`
quality flag. A later plan-only response cannot replace an already stored
realtime delay or cancellation. A trusted realtime response can still correct
an earlier prediction, including correcting a delay back to zero.

Run the migration once after updating an existing installation:

```bash
cd /home/pi/BahnProjekt/filedforBahnprojekt
../.venv/bin/python migrate_train_db.py
```

The migration is idempotent and does not delete old snapshot rows. It assigns
an event key only to the latest existing row for each logical event.

After a backup, old imported snapshots can be converted physically to one row
per logical event:

```bash
../.venv/bin/python compact_train_db.py
../.venv/bin/python compact_train_db.py --apply --optimize
```

The first command is a dry run. The apply command retains the newest row for
each station, trip id, planned date, and planned time. Multiple runs of the same
line remain separate because their planned times differ.

## Raspberry Pi scraper

Install the Python and frontend dependencies first. `NODE_EXECUTABLE=auto`
finds both the Windows npm Bun binary and the Linux/ARM64 npm Bun binary.

Typical upgrade sequence:

```bash
cd /home/pi/BahnProjekt
git pull
.venv/bin/pip install -r filedforBahnprojekt/requirements.txt
cd filedforBahnprojekt/my-app
npm ci
npm run build
cd ..
../.venv/bin/python migrate_train_db.py
```

The database account used for the migration needs `ALTER`, `CREATE`, `INDEX`,
`SELECT`, and `UPDATE` privileges. The regular scraper only needs its normal
read/write privileges after the migration.

Test the board provider without writing:

```bash
../.venv/bin/python scrape_train_data.py \
  --stations-file scrape_stations.txt \
  --dry-run
```

Start the continuous scraper:

```bash
../.venv/bin/python scrape_train_data.py \
  --stations-file scrape_stations.txt \
  --interval 600
```

To run the live and finalization windows immediately during a manual check:

```bash
../.venv/bin/python scrape_train_data.py \
  --stations-file scrape_stations.txt \
  --finalize-now \
  --dry-run
```

The Pi defaults use one persistent Bun process, one station at a time, and
automatic rate-limit retries. Arrival and departure boards of that station are
fetched together. Each cycle reads a live 60-minute window beginning 45 minutes
in the past, so a train is observed repeatedly after its planned time. Every
third cycle also reads a separate 60-minute finalization
window beginning three hours in the past. This is necessary because DB Web
effectively limits one station-board request to about one hour even when a
larger duration is requested.

The finalization window lets already departed trains receive their final delay
or cancellation state without multiplying every cycle into four historical
requests. These values can be changed in `.env`:

```dotenv
SCRAPE_WORKERS=1
SCRAPE_STATION_PAUSE_MS=750
SCRAPE_RETRY_ATTEMPTS=4
SCRAPE_LOOKBACK_MINUTES=45
SCRAPE_DURATION_MINUTES=60
SCRAPE_RESULTS=120
SCRAPE_FINALIZE_LOOKBACK_MINUTES=180
SCRAPE_FINALIZE_EVERY=3
SCRAPE_RUN_RETENTION_DAYS=30
```

An example systemd unit is available at
`filedforBahnprojekt/deploy/onpoint-scraper.service.example`. Adjust its user
and paths, copy it to `/etc/systemd/system/onpoint-scraper.service`, then run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now onpoint-scraper
```

A matching one-worker Gunicorn unit is available at
`filedforBahnprojekt/deploy/onpoint-backend.service.example`.

Scrape health is stored once per station request in `scrape_runs`. The old
per-departure `logs` table is left untouched for compatibility but receives no
new rows. Health rows older than 30 days are deleted automatically by default.

