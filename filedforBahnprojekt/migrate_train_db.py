import argparse
import os
from pathlib import Path

import mysql.connector

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


PROJECT_DIR = Path(__file__).resolve().parent


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
        description="Upgrade TrainDB for compact station-board UPSERTs."
    )
    parser.add_argument(
        "--skip-backfill",
        action="store_true",
        help="Add the schema without assigning event keys to existing rows.",
    )
    return parser.parse_args()


def column_exists(cursor, table, column):
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        LIMIT 1
        """,
        (table, column),
    )
    return cursor.fetchone() is not None


def index_exists(cursor, table, index):
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND INDEX_NAME = %s
        LIMIT 1
        """,
        (table, index),
    )
    return cursor.fetchone() is not None


def add_column(cursor, table, column, definition):
    if column_exists(cursor, table, column):
        return

    print(f"Adding {table}.{column}")
    cursor.execute(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}")


def add_index(cursor, table, index, definition):
    if index_exists(cursor, table, index):
        return

    print(f"Adding index {table}.{index}")
    cursor.execute(f"ALTER TABLE `{table}` ADD {definition}")


def create_scrape_runs(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS scrape_runs (
            scrape_run_id BIGINT NOT NULL AUTO_INCREMENT,
            station_query VARCHAR(255) NOT NULL,
            provider_station_id VARCHAR(64) NULL,
            board_time DATETIME NOT NULL,
            mode VARCHAR(16) NOT NULL,
            fetched_count INT NOT NULL DEFAULT 0,
            inserted_count INT NOT NULL DEFAULT 0,
            updated_count INT NOT NULL DEFAULT 0,
            unchanged_count INT NOT NULL DEFAULT 0,
            error_message VARCHAR(1000) NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (scrape_run_id),
            KEY idx_scrape_runs_created_at (created_at),
            KEY idx_scrape_runs_station (provider_station_id, created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )


def backfill_latest_event_keys(cursor, table, event_type):
    id_column = "departure_id" if event_type == "departure" else "arrival_id"
    planned_time_column = f"planned_{event_type}"
    planned_date_column = f"planned_{event_type}_date"

    print(f"Backfilling latest logical events in {table}")
    cursor.execute(
        f"""
        UPDATE `{table}` AS target
        JOIN (
            SELECT latest_id
            FROM (
                SELECT MAX(`{id_column}`) AS latest_id
                FROM `{table}`
                WHERE trip_id IS NOT NULL
                  AND trip_id <> ''
                  AND `{planned_time_column}` IS NOT NULL
                  AND `{planned_date_column}` IS NOT NULL
                GROUP BY
                    station_id,
                    trip_id,
                    `{planned_date_column}`,
                    `{planned_time_column}`
            ) AS grouped_events
        ) AS latest_event
          ON latest_event.latest_id = target.`{id_column}`
        SET target.event_key = UNHEX(
            SHA2(
                CONCAT(
                    '{event_type}',
                    '|',
                    target.station_id,
                    '|',
                    target.trip_id,
                    '|',
                    DATE_FORMAT(target.`{planned_date_column}`, '%Y-%m-%d'),
                    'T',
                    TIME_FORMAT(target.`{planned_time_column}`, '%H:%i:%S')
                ),
                256
            )
        )
        """
    )
    print(f"Assigned {cursor.rowcount} event keys in {table}")


def backfill_realtime_quality(cursor, table, event_type):
    planned_time_column = f"planned_{event_type}"
    actual_time_column = f"actual_{event_type}"
    planned_date_column = f"planned_{event_type}_date"
    actual_date_column = f"actual_{event_type}_date"

    cursor.execute(
        f"""
        UPDATE `{table}`
        SET realtime_known = 1
        WHERE realtime_known = 0
          AND (
              cancelled = 1
              OR COALESCE(delay_minutes, 0) <> 0
              OR NOT (`{actual_time_column}` <=> `{planned_time_column}`)
              OR NOT (`{actual_date_column}` <=> `{planned_date_column}`)
          )
        """
    )
    print(f"Marked {cursor.rowcount} historical realtime rows in {table}")


def migrate(connection, skip_backfill=False):
    cursor = connection.cursor()
    try:
        add_column(cursor, "stations", "provider_station_id", "VARCHAR(64) NULL")

        for table in ("arrivals", "departures"):
            add_column(cursor, table, "event_key", "BINARY(32) NULL")
            add_column(
                cursor,
                table,
                "cancelled",
                "TINYINT(1) NOT NULL DEFAULT 0",
            )
            add_column(cursor, table, "observed_at", "DATETIME NULL")
            add_column(
                cursor,
                table,
                "realtime_known",
                "TINYINT(1) NOT NULL DEFAULT 0",
            )

        create_scrape_runs(cursor)
        connection.commit()

        backfill_realtime_quality(cursor, "arrivals", "arrival")
        backfill_realtime_quality(cursor, "departures", "departure")
        connection.commit()

        if not skip_backfill:
            backfill_latest_event_keys(cursor, "arrivals", "arrival")
            connection.commit()
            backfill_latest_event_keys(cursor, "departures", "departure")
            connection.commit()

        add_index(
            cursor,
            "stations",
            "uq_stations_provider_station_id",
            "UNIQUE KEY uq_stations_provider_station_id (provider_station_id)",
        )
        add_index(
            cursor,
            "arrivals",
            "uq_arrivals_event_key",
            "UNIQUE KEY uq_arrivals_event_key (event_key)",
        )
        add_index(
            cursor,
            "departures",
            "uq_departures_event_key",
            "UNIQUE KEY uq_departures_event_key (event_key)",
        )
        add_index(
            cursor,
            "arrivals",
            "idx_arrivals_station_train_latest",
            "KEY idx_arrivals_station_train_latest (station_id, train_id, arrival_id)",
        )
        add_index(
            cursor,
            "departures",
            "idx_departures_station_train_latest",
            "KEY idx_departures_station_train_latest (station_id, train_id, departure_id)",
        )
        connection.commit()
    finally:
        cursor.close()


def main():
    args = parse_args()
    connection = mysql.connector.connect(**db_config())
    try:
        migrate(connection, skip_backfill=args.skip_backfill)
    finally:
        connection.close()

    print("TrainDB migration completed.")


if __name__ == "__main__":
    main()
