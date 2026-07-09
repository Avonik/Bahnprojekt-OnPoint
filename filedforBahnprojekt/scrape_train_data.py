import argparse
import datetime as dt
import json
import os
import subprocess
import time
from pathlib import Path

import mysql.connector

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


PROJECT_DIR = Path(__file__).resolve().parent
NODE_BOARD_SCRIPT = PROJECT_DIR / "my-app" / "dbweb_station_board.mjs"


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

DEFAULT_STATIONS = [
    "Braunschweig Hbf",
    "Bremen Hbf",
    "Celle",
    "Emden Hbf",
    "G\u00f6ttingen",
    "Hamburg Hbf",
    "Hamburg-Harburg",
    "Hameln",
    "Hannover Hbf",
    "Hildesheim Hbf",
    "Kiel Hbf",
    "Leer(Ostfriesl)",
    "Lingen(Ems)",
    "L\u00fcneburg",
    "Magdeburg Hbf",
    "Minden(Westf)",
    "M\u00fcnster(Westf) Hbf",
    "Nienburg(Weser)",
    "Oldenburg(Oldb)",
    "Osnabr\u00fcck Hbf",
    "Rheine",
    "Stendal Hbf",
    "Uelzen",
    "Wolfsburg Hbf",
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
        description="Scrape DB station boards into the TrainDB arrivals/departures history tables."
    )
    parser.add_argument("--stations", nargs="*", help="Station names to scrape. Defaults to the planner station list.")
    parser.add_argument("--stations-file", help="Text file with one station name per line.")
    parser.add_argument("--mode", choices=["both", "departures", "arrivals"], default="both")
    parser.add_argument("--duration", type=int, default=60, help="Minutes of station-board data to request.")
    parser.add_argument("--results", type=int, default=80, help="Maximum board entries requested per station and board.")
    parser.add_argument("--interval", type=int, default=0, help="Repeat every N seconds. 0 means one run.")
    parser.add_argument("--when", help="ISO timestamp to scrape from. Defaults to now.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and print counts without writing to MySQL.")
    parser.add_argument("--dedupe", action="store_true", help="Skip rows already seen with the same station/train/trip/time.")
    return parser.parse_args()


def load_stations(args):
    stations = []

    if args.stations_file:
        path = Path(args.stations_file)
        stations.extend(
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

    if args.stations:
        stations.extend(args.stations)

    return stations or DEFAULT_STATIONS


def table_columns(cursor, table):
    cursor.execute(f"SHOW COLUMNS FROM `{table}`")
    return {row[0] for row in cursor.fetchall()}


def first_existing(columns, candidates):
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def fetch_station_board(station, mode, when_iso, duration, results):
    command = [
        os.getenv("NODE_EXECUTABLE", "node"),
        str(NODE_BOARD_SCRIPT),
        station,
        mode,
        when_iso,
        str(duration),
        str(results),
    ]

    completed = subprocess.run(
        command,
        cwd=str(PROJECT_DIR / "my-app"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(detail or f"station board provider exited with code {completed.returncode}")

    return json.loads(completed.stdout)


def parse_iso(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def get_or_create_station(cursor, columns, event):
    cursor.execute("SELECT station_id FROM stations WHERE station_name = %s", (event["station_name"],))
    result = cursor.fetchone()
    if result:
        return result[0]

    fields = ["station_name"]
    values = [event["station_name"]]

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
    return cursor.lastrowid


def get_or_create_train(cursor, columns, event):
    cursor.execute("SELECT train_id FROM trains WHERE train_name = %s", (event["train_name"],))
    result = cursor.fetchone()
    if result:
        return result[0]

    fields = ["train_name"]
    values = [event["train_name"]]

    if "train_direction" in columns:
        fields.append("train_direction")
        values.append(event.get("train_direction") or "")

    placeholders = ", ".join(["%s"] * len(fields))
    cursor.execute(
        f"INSERT INTO trains ({', '.join(fields)}) VALUES ({placeholders})",
        values,
    )
    return cursor.lastrowid


def row_exists(cursor, table, values):
    cursor.execute(
        f"""
        SELECT 1
        FROM {table}
        WHERE station_id = %s
          AND train_id = %s
          AND trip_id = %s
          AND {values["planned_time_column"]} = %s
        LIMIT 1
        """,
        (
            values["station_id"],
            values["train_id"],
            values["trip_id"],
            values["planned_time"],
        ),
    )
    return cursor.fetchone() is not None


def insert_log(cursor, schemas, departure_id, check_time):
    if "logs" not in schemas:
        return

    columns = schemas["logs"]
    if "departure_id" not in columns or "check_time" not in columns:
        return

    cursor.execute(
        "INSERT INTO logs (departure_id, check_time) VALUES (%s, %s)",
        (departure_id, check_time.replace(tzinfo=None)),
    )


def insert_event(cursor, schemas, event, dedupe, check_time):
    table = "departures" if event["type"] == "departure" else "arrivals"
    columns = schemas[table]
    prefix = event["type"]
    planned_dt = parse_iso(event["planned_time"])
    actual_dt = parse_iso(event["actual_time"])

    planned_time_col = first_existing(columns, [f"planned_{prefix}"])
    actual_time_col = first_existing(columns, [f"actual_{prefix}"])
    planned_date_col = first_existing(columns, [f"planned_{prefix}_date", "planned_date"])
    actual_date_col = first_existing(columns, [f"actual_{prefix}_date", "actual_date"])

    if not planned_time_col or not actual_time_col:
        raise RuntimeError(f"Table {table} is missing planned/actual {prefix} time columns")

    station_id = get_or_create_station(cursor, schemas["stations"], event)
    train_id = get_or_create_train(cursor, schemas["trains"], event)

    row = {
        "station_id": station_id,
        "train_id": train_id,
        "trip_id": event["trip_id"],
        "planned_time_column": planned_time_col,
        "planned_time": planned_dt.time().replace(microsecond=0),
    }

    if dedupe and row_exists(cursor, table, row):
        return False

    fields = ["station_id", "train_id", planned_time_col, actual_time_col, "delay_minutes", "trip_id"]
    values = [
        station_id,
        train_id,
        planned_dt.time().replace(microsecond=0),
        actual_dt.time().replace(microsecond=0),
        event.get("delay_minutes", 0),
        event["trip_id"],
    ]

    if planned_date_col:
        fields.append(planned_date_col)
        values.append(planned_dt.date())

    if actual_date_col:
        fields.append(actual_date_col)
        values.append(actual_dt.date())

    placeholders = ", ".join(["%s"] * len(fields))
    cursor.execute(
        f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({placeholders})",
        values,
    )

    if table == "departures":
        insert_log(cursor, schemas, cursor.lastrowid, check_time)

    return True


def scrape_once(args, stations):
    when_iso = args.when or dt.datetime.now().astimezone().isoformat(timespec="seconds")
    connection = mysql.connector.connect(**db_config())
    cursor = connection.cursor()
    schemas = {
        "stations": table_columns(cursor, "stations"),
        "trains": table_columns(cursor, "trains"),
        "arrivals": table_columns(cursor, "arrivals"),
        "departures": table_columns(cursor, "departures"),
        "logs": table_columns(cursor, "logs"),
    }

    total_seen = 0
    total_inserted = 0

    try:
        for station in stations:
            try:
                payload = fetch_station_board(station, args.mode, when_iso, args.duration, args.results)
                events = payload.get("events", [])
                total_seen += len(events)

                if args.dry_run:
                    print(f"{station}: fetched {len(events)} events")
                    continue

                inserted = 0
                check_time = dt.datetime.now().astimezone()
                for event in events:
                    if insert_event(cursor, schemas, event, args.dedupe, check_time):
                        inserted += 1

                connection.commit()
                total_inserted += inserted
                print(f"{station}: fetched {len(events)}, inserted {inserted}")
            except Exception as error:
                connection.rollback()
                print(f"{station}: skipped ({error})")
    finally:
        cursor.close()
        connection.close()

    print(f"Done. fetched={total_seen}, inserted={total_inserted}, when={when_iso}")


def main():
    args = parse_args()
    stations = load_stations(args)

    while True:
        scrape_once(args, stations)

        if args.interval <= 0:
            break

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
