import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import mysql.connector

from javascript_runtime import resolve_javascript_runtime

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


PROJECT_DIR = Path(__file__).resolve().parent
NODE_BOARD_SCRIPT = PROJECT_DIR / "my-app" / "dbweb_station_board.mjs"
DEFAULT_STATIONS_FILE = PROJECT_DIR / "scrape_stations.txt"


def load_local_env(path):
    if load_dotenv:
        load_dotenv(path)
        return

    path = Path(path)
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


load_local_env(PROJECT_DIR / ".env")
JAVASCRIPT_RUNTIME = resolve_javascript_runtime(PROJECT_DIR)

# Planner endpoints and empirically frequent transfer stations are deliberately
# kept in one default scrape set for now. A stations file can override this set
# on small Raspberry Pi installations.
DEFAULT_SCRAPE_STATIONS = [
    "Braunschweig Hbf",
    "Bremen Hbf",
    "Celle",
    "Emden Hbf",
    "Göttingen",
    "Hamburg Hbf",
    "Hamburg-Harburg",
    "Hameln",
    "Hannover Hbf",
    "Hildesheim Hbf",
    "Kiel Hbf",
    "Leer(Ostfriesl)",
    "Lingen(Ems)",
    "Lüneburg",
    "Magdeburg Hbf",
    "Minden(Westf)",
    "Münster(Westf) Hbf",
    "Nienburg(Weser)",
    "Oldenburg(Oldb)Hbf",
    "Osnabrück Hbf",
    "Rheine",
    "Stendal Hbf",
    "Uelzen",
    "Wolfsburg Hbf",
    "Hamm(Westf)Hbf",
    "Löhne(Westf)",
    "Paderborn Hbf",
    "Altenbeken",
    "Lehrte",
    "Verden(Aller)",
    "Rotenburg(Wümme)",
    "Herford",
]


def db_config():
    return {
        "host": os.getenv("TRAINDB_HOST", "localhost"),
        "port": int(os.getenv("TRAINDB_PORT", "3306")),
        "user": os.getenv("TRAINDB_USER", "bahnapp"),
        "password": os.getenv("TRAINDB_PASSWORD", ""),
        "database": os.getenv("TRAINDB_DATABASE", "TrainDB"),
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape DB station boards into compact TrainDB event rows."
    )
    parser.add_argument(
        "--stations",
        nargs="*",
        help="Station names to scrape. Defaults to endpoints plus important transfer stations.",
    )
    parser.add_argument("--stations-file", help="Text file with one station name per line.")
    parser.add_argument("--mode", choices=["both", "departures", "arrivals"], default="both")
    parser.add_argument(
        "--lookback",
        type=int,
        default=int(os.getenv("SCRAPE_LOOKBACK_MINUTES", "45")),
        help="Start the live board window this many minutes in the past.",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=int(os.getenv("SCRAPE_DURATION_MINUTES", "60")),
        help="Minutes per board window. DB Web effectively caps one window near 60 minutes.",
    )
    parser.add_argument(
        "--results",
        type=int,
        default=int(os.getenv("SCRAPE_RESULTS", "120")),
        help="Maximum board entries requested per station and board.",
    )
    parser.add_argument(
        "--finalize-lookback",
        type=int,
        default=int(os.getenv("SCRAPE_FINALIZE_LOOKBACK_MINUTES", "180")),
        help="Age in minutes of the additional historical finalization window.",
    )
    parser.add_argument(
        "--finalize-every",
        type=int,
        default=int(os.getenv("SCRAPE_FINALIZE_EVERY", "3")),
        help="Run the finalization window every N cycles. 0 disables it.",
    )
    parser.add_argument(
        "--finalize-now",
        action="store_true",
        help="Include the historical finalization window in this run.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.getenv("SCRAPE_WORKERS", "1")),
        help="Concurrent station requests within the shared Bun process.",
    )
    parser.add_argument(
        "--scrape-run-retention-days",
        type=int,
        default=int(os.getenv("SCRAPE_RUN_RETENTION_DAYS", "30")),
        help="Delete scrape health rows older than this many days. 0 disables cleanup.",
    )
    parser.add_argument("--interval", type=int, default=0, help="Repeat every N seconds. 0 means one run.")
    parser.add_argument(
        "--when",
        help="ISO timestamp at which the board window starts. Defaults to now minus --lookback.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Fetch and print counts without writing to MySQL.")
    parser.add_argument(
        "--dedupe",
        action="store_true",
        help="Deprecated compatibility flag. The scraper always performs safe UPSERTs.",
    )
    return parser.parse_args()


def load_stations(args):
    stations = []

    stations_file = Path(args.stations_file) if args.stations_file else None
    if not stations_file and not args.stations and DEFAULT_STATIONS_FILE.exists():
        stations_file = DEFAULT_STATIONS_FILE

    if stations_file:
        path = stations_file
        stations.extend(
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

    if args.stations:
        stations.extend(args.stations)

    return list(dict.fromkeys(stations or DEFAULT_SCRAPE_STATIONS))


def table_columns(cursor, table):
    cursor.execute(f"SHOW COLUMNS FROM `{table}`")
    return {row[0] for row in cursor.fetchall()}


def table_exists(cursor, table):
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
        LIMIT 1
        """,
        (table,),
    )
    return cursor.fetchone() is not None


def first_existing(columns, candidates):
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def validate_schema(schemas):
    missing = []
    if "provider_station_id" not in schemas["stations"]:
        missing.append("stations.provider_station_id")

    for table in ("arrivals", "departures"):
        for column in ("event_key", "cancelled", "observed_at", "realtime_known"):
            if column not in schemas[table]:
                missing.append(f"{table}.{column}")

    if missing:
        raise RuntimeError(
            "TrainDB schema is missing "
            + ", ".join(missing)
            + ". Run: python migrate_train_db.py"
        )


def fetch_station_boards(stations, args, windows):
    requests = []
    request_metadata = {}
    request_id = 0
    for station_index, station in enumerate(stations):
        for window in windows:
            requests.append(
                {
                    "id": request_id,
                    "station": station,
                    "mode": args.mode,
                    "when": window["start"].isoformat(timespec="seconds"),
                    "duration": args.duration,
                    "results": args.results,
                }
            )
            request_metadata[request_id] = (station_index, window["name"])
            request_id += 1

    command = [
        JAVASCRIPT_RUNTIME,
        str(NODE_BOARD_SCRIPT),
        "--batch",
        str(max(1, args.workers)),
    ]
    timeout_seconds = max(180, len(requests) * 20)
    completed = subprocess.run(
        command,
        cwd=str(PROJECT_DIR / "my-app"),
        input=json.dumps({"requests": requests}, ensure_ascii=False),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout_seconds,
        check=False,
    )

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(
            detail or f"station board provider exited with code {completed.returncode}"
        )

    payload = json.loads(completed.stdout)
    aggregated = [
        {
            "query": station,
            "station": None,
            "events": [],
            "errors": [],
            "windows": [],
        }
        for station in stations
    ]
    seen_response_ids = set()

    for response in payload.get("responses", []):
        response_id = response.get("id")
        metadata = request_metadata.get(response_id)
        if metadata is None:
            continue

        seen_response_ids.add(response_id)
        station_index, window_name = metadata
        station_result = aggregated[station_index]
        station_result["windows"].append(window_name)
        if response.get("error"):
            station_result["errors"].append(f"{window_name}: {response['error']}")

        station_result["station"] = response.get("station") or station_result["station"]
        station_result["events"].extend(response.get("events", []))

    for response_id, (station_index, window_name) in request_metadata.items():
        if response_id not in seen_response_ids:
            aggregated[station_index]["errors"].append(
                f"{window_name}: Station board provider returned no response."
            )

    for station_result in aggregated:
        unique_events = {}
        for event in station_result["events"]:
            identity = (
                event.get("type"),
                event.get("station_id"),
                event.get("trip_id"),
                event.get("planned_time"),
            )
            unique_events[identity] = event
        station_result["events"] = list(unique_events.values())
        if station_result["errors"]:
            station_result["error"] = " | ".join(station_result["errors"])

    return aggregated


def parse_iso(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def event_key(event_type, station_id, trip_id, planned_dt):
    identity = (
        f"{event_type}|{station_id}|{trip_id}|"
        f"{planned_dt.strftime('%Y-%m-%dT%H:%M:%S')}"
    )
    return hashlib.sha256(identity.encode("utf-8")).digest()


def get_or_create_station(cursor, columns, event, cache):
    provider_station_id = str(event.get("station_id") or "").strip()
    station_name = event["station_name"]

    if provider_station_id:
        cache_key = ("provider", provider_station_id)
        if cache_key in cache:
            return cache[cache_key]

        cursor.execute(
            "SELECT station_id FROM stations WHERE provider_station_id = %s",
            (provider_station_id,),
        )
        result = cursor.fetchone()
        if result:
            cache[cache_key] = result[0]
            cache[("name", station_name)] = result[0]
            return result[0]

    name_cache_key = ("name", station_name)
    if name_cache_key in cache:
        return cache[name_cache_key]

    cursor.execute(
        "SELECT station_id, provider_station_id FROM stations WHERE station_name = %s",
        (station_name,),
    )
    result = cursor.fetchone()
    if result:
        station_id = result[0]
        if provider_station_id and not result[1]:
            cursor.execute(
                """
                UPDATE stations
                SET provider_station_id = %s
                WHERE station_id = %s
                  AND provider_station_id IS NULL
                """,
                (provider_station_id, station_id),
            )
        cache[name_cache_key] = station_id
        if provider_station_id:
            cache[("provider", provider_station_id)] = station_id
        return station_id

    fields = ["station_name"]
    values = [station_name]

    if provider_station_id and "provider_station_id" in columns:
        fields.append("provider_station_id")
        values.append(provider_station_id)

    latitude_col = first_existing(columns, ["latitude", "lat", "station_latitude"])
    longitude_col = first_existing(columns, ["longitude", "lon", "station_longitude"])

    if latitude_col and event.get("latitude") is not None:
        fields.append(latitude_col)
        values.append(event["latitude"])

    if longitude_col and event.get("longitude") is not None:
        fields.append(longitude_col)
        values.append(event["longitude"])

    placeholders = ", ".join(["%s"] * len(fields))
    cursor.execute(
        f"INSERT INTO stations ({', '.join(fields)}) VALUES ({placeholders})",
        values,
    )
    station_id = cursor.lastrowid
    cache[name_cache_key] = station_id
    if provider_station_id:
        cache[("provider", provider_station_id)] = station_id
    return station_id


def get_or_create_train(cursor, columns, event, cache):
    train_name = event["train_name"]
    if train_name in cache:
        return cache[train_name]

    cursor.execute("SELECT train_id FROM trains WHERE train_name = %s", (train_name,))
    result = cursor.fetchone()
    if result:
        cache[train_name] = result[0]
        return result[0]

    fields = ["train_name"]
    values = [train_name]

    if "train_direction" in columns:
        fields.append("train_direction")
        values.append(event.get("train_direction") or "")

    placeholders = ", ".join(["%s"] * len(fields))
    cursor.execute(
        f"INSERT INTO trains ({', '.join(fields)}) VALUES ({placeholders})",
        values,
    )
    train_id = cursor.lastrowid
    cache[train_name] = train_id
    return train_id


def upsert_event(cursor, schemas, event, observed_at, station_cache, train_cache):
    table = "departures" if event["type"] == "departure" else "arrivals"
    columns = schemas[table]
    prefix = event["type"]
    planned_dt = parse_iso(event["planned_time"])
    actual_dt = parse_iso(event["actual_time"])

    planned_time_col = first_existing(columns, [f"planned_{prefix}"])
    actual_time_col = first_existing(columns, [f"actual_{prefix}"])
    planned_date_col = first_existing(
        columns, [f"planned_{prefix}_date", "planned_date"]
    )
    actual_date_col = first_existing(
        columns, [f"actual_{prefix}_date", "actual_date"]
    )

    if not planned_time_col or not actual_time_col:
        raise RuntimeError(
            f"Table {table} is missing planned/actual {prefix} time columns"
        )
    if not planned_date_col or not actual_date_col:
        raise RuntimeError(f"Table {table} is missing planned/actual date columns")

    station_id = get_or_create_station(
        cursor, schemas["stations"], event, station_cache
    )
    train_id = get_or_create_train(cursor, schemas["trains"], event, train_cache)
    key = event_key(prefix, station_id, event["trip_id"], planned_dt)

    fields = [
        "station_id",
        "train_id",
        planned_time_col,
        actual_time_col,
        "delay_minutes",
        "trip_id",
        planned_date_col,
        actual_date_col,
        "event_key",
        "cancelled",
        "realtime_known",
        "observed_at",
    ]
    values = [
        station_id,
        train_id,
        planned_dt.time().replace(microsecond=0),
        actual_dt.time().replace(microsecond=0),
        event.get("delay_minutes", 0),
        event["trip_id"],
        planned_dt.date(),
        actual_dt.date(),
        key,
        bool(event.get("cancelled")),
        bool(event.get("realtime_known")),
        observed_at.replace(tzinfo=None),
    ]
    placeholders = ", ".join(["%s"] * len(fields))
    cursor.execute(
        f"""
        INSERT INTO {table} ({", ".join(fields)})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE
            observed_at = IF(
                (
                    VALUES(realtime_known) = 1
                    OR realtime_known = 0
                )
                AND (
                    observed_at IS NULL
                    OR NOT (train_id <=> VALUES(train_id))
                    OR NOT ({actual_time_col} <=> VALUES({actual_time_col}))
                    OR NOT ({actual_date_col} <=> VALUES({actual_date_col}))
                    OR NOT (delay_minutes <=> VALUES(delay_minutes))
                    OR NOT (cancelled <=> VALUES(cancelled))
                    OR NOT (realtime_known <=> VALUES(realtime_known))
                ),
                VALUES(observed_at),
                observed_at
            ),
            train_id = VALUES(train_id),
            {actual_time_col} = IF(
                VALUES(realtime_known) = 1 OR realtime_known = 0,
                VALUES({actual_time_col}),
                {actual_time_col}
            ),
            {actual_date_col} = IF(
                VALUES(realtime_known) = 1 OR realtime_known = 0,
                VALUES({actual_date_col}),
                {actual_date_col}
            ),
            delay_minutes = IF(
                VALUES(realtime_known) = 1 OR realtime_known = 0,
                VALUES(delay_minutes),
                delay_minutes
            ),
            cancelled = IF(
                VALUES(realtime_known) = 1 OR realtime_known = 0,
                VALUES(cancelled),
                cancelled
            ),
            realtime_known = GREATEST(
                realtime_known,
                VALUES(realtime_known)
            )
        """,
        values,
    )

    if cursor.rowcount == 1:
        return "inserted"
    if cursor.rowcount == 2:
        return "updated"
    return "unchanged"


def insert_scrape_run(
    cursor,
    schemas,
    station_query,
    provider_station_id,
    board_time,
    mode,
    counts,
    error_message=None,
):
    if "scrape_runs" not in schemas:
        return

    cursor.execute(
        """
        INSERT INTO scrape_runs (
            station_query,
            provider_station_id,
            board_time,
            mode,
            fetched_count,
            inserted_count,
            updated_count,
            unchanged_count,
            error_message
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            station_query,
            provider_station_id or None,
            board_time.replace(tzinfo=None),
            mode,
            counts.get("fetched", 0),
            counts.get("inserted", 0),
            counts.get("updated", 0),
            counts.get("unchanged", 0),
            str(error_message)[:1000] if error_message else None,
        ),
    )


def cleanup_scrape_runs(cursor, schemas, retention_days):
    if "scrape_runs" not in schemas or retention_days <= 0:
        return 0

    cursor.execute(
        """
        DELETE FROM scrape_runs
        WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
        """,
        (retention_days,),
    )
    return cursor.rowcount


def scrape_once(args, stations, cycle_number=0):
    now = dt.datetime.now().astimezone()
    if args.when:
        windows = [{"name": "manual", "start": parse_iso(args.when)}]
    else:
        windows = [
            {
                "name": "live",
                "start": now - dt.timedelta(minutes=max(0, args.lookback)),
            }
        ]
        if (
            args.finalize_now
            or (
                args.finalize_every > 0
                and cycle_number > 0
                and cycle_number % args.finalize_every == 0
            )
        ):
            windows.append(
                {
                    "name": "finalize",
                    "start": now
                    - dt.timedelta(minutes=max(0, args.finalize_lookback)),
                }
            )

    board_start = windows[0]["start"]
    window_summary = ",".join(
        f"{window['name']}={window['start'].isoformat(timespec='seconds')}"
        for window in windows
    )
    responses = fetch_station_boards(stations, args, windows)

    total_counts = {
        "fetched": 0,
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
        "errors": 0,
    }

    if args.dry_run:
        for station, response in zip(stations, responses):
            events = response.get("events", [])
            if response.get("error") and not events:
                total_counts["errors"] += 1
                print(f"{station}: skipped ({response['error']})")
                continue
            if response.get("error"):
                total_counts["errors"] += 1
            fetched = len(events)
            total_counts["fetched"] += fetched
            suffix = f", partial error: {response['error']}" if response.get("error") else ""
            print(f"{station}: fetched {fetched} events{suffix}")
        print(
            f"Done. fetched={total_counts['fetched']}, errors={total_counts['errors']}, "
            f"windows={window_summary}, dry_run=true"
        )
        return

    connection = mysql.connector.connect(**db_config())
    cursor = connection.cursor()
    schemas = {
        "stations": table_columns(cursor, "stations"),
        "trains": table_columns(cursor, "trains"),
        "arrivals": table_columns(cursor, "arrivals"),
        "departures": table_columns(cursor, "departures"),
    }
    if table_exists(cursor, "scrape_runs"):
        schemas["scrape_runs"] = table_columns(cursor, "scrape_runs")
    validate_schema(schemas)

    station_cache = {}
    train_cache = {}
    try:
        for station, response in zip(stations, responses):
            counts = {
                "fetched": 0,
                "inserted": 0,
                "updated": 0,
                "unchanged": 0,
            }
            provider_station_id = str(
                (response.get("station") or {}).get("id") or ""
            )

            events = response.get("events", [])
            if response.get("error") and not events:
                total_counts["errors"] += 1
                insert_scrape_run(
                    cursor,
                    schemas,
                    station,
                    provider_station_id,
                    board_start,
                    args.mode,
                    counts,
                    response["error"],
                )
                connection.commit()
                print(f"{station}: skipped ({response['error']})")
                continue
            if response.get("error"):
                total_counts["errors"] += 1

            counts["fetched"] = len(events)
            total_counts["fetched"] += len(events)

            try:
                observed_at = dt.datetime.now().astimezone()
                for event in events:
                    state = upsert_event(
                        cursor,
                        schemas,
                        event,
                        observed_at,
                        station_cache,
                        train_cache,
                    )
                    counts[state] += 1

                insert_scrape_run(
                    cursor,
                    schemas,
                    station,
                    provider_station_id,
                    board_start,
                    args.mode,
                    counts,
                    response.get("error"),
                )
                connection.commit()
                for state in ("inserted", "updated", "unchanged"):
                    total_counts[state] += counts[state]
                print(
                    f"{station}: fetched {counts['fetched']}, "
                    f"inserted {counts['inserted']}, updated {counts['updated']}, "
                    f"unchanged {counts['unchanged']}"
                    + (
                        f", partial error: {response['error']}"
                        if response.get("error")
                        else ""
                    )
                )
            except Exception as error:
                connection.rollback()
                total_counts["errors"] += 1
                insert_scrape_run(
                    cursor,
                    schemas,
                    station,
                    provider_station_id,
                    board_start,
                    args.mode,
                    counts,
                    error,
                )
                connection.commit()
                print(f"{station}: skipped ({error})")

        if cycle_number % 24 == 0:
            deleted_runs = cleanup_scrape_runs(
                cursor,
                schemas,
                args.scrape_run_retention_days,
            )
            connection.commit()
            if deleted_runs:
                print(f"scrape_runs: removed {deleted_runs} expired rows")
    finally:
        cursor.close()
        connection.close()

    print(
        "Done. "
        f"fetched={total_counts['fetched']}, "
        f"inserted={total_counts['inserted']}, "
        f"updated={total_counts['updated']}, "
        f"unchanged={total_counts['unchanged']}, "
        f"errors={total_counts['errors']}, "
        f"windows={window_summary}"
    )


def main():
    args = parse_args()
    stations = load_stations(args)

    if args.dedupe:
        print("--dedupe is deprecated; safe UPSERTs are always enabled.")

    cycle_number = 0
    while True:
        scrape_once(args, stations, cycle_number)
        cycle_number += 1

        if args.interval <= 0:
            break

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
