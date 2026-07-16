import argparse

import mysql.connector

from migrate_train_db import db_config


EVENT_TABLES = {
    "arrivals": {
        "id": "arrival_id",
        "planned_date": "planned_arrival_date",
        "planned_time": "planned_arrival",
    },
    "departures": {
        "id": "departure_id",
        "planned_date": "planned_departure_date",
        "planned_time": "planned_departure",
    },
}


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Compact imported TrainDB snapshots to one latest row per "
            "station/trip/planned date/time."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Delete obsolete snapshots. Without this flag only counts are shown.",
    )
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="Run OPTIMIZE TABLE after deletion to return free pages to disk.",
    )
    return parser.parse_args()


def obsolete_count(cursor, table, columns):
    cursor.execute(
        f"""
        SELECT COALESCE(SUM(snapshot_count - 1), 0)
        FROM (
            SELECT COUNT(*) AS snapshot_count
            FROM `{table}`
            WHERE trip_id IS NOT NULL
              AND trip_id <> ''
              AND `{columns["planned_date"]}` IS NOT NULL
              AND `{columns["planned_time"]}` IS NOT NULL
            GROUP BY
                station_id,
                trip_id,
                `{columns["planned_date"]}`,
                `{columns["planned_time"]}`
            HAVING COUNT(*) > 1
        ) AS duplicate_events
        """
    )
    return int(cursor.fetchone()[0] or 0)


def delete_obsolete_snapshots(cursor, table, columns):
    temp_table = f"obsolete_{table}"
    id_column = columns["id"]
    cursor.execute(f"DROP TEMPORARY TABLE IF EXISTS `{temp_table}`")
    cursor.execute(
        f"""
        CREATE TEMPORARY TABLE `{temp_table}` (
            event_id INT NOT NULL PRIMARY KEY
        ) ENGINE=InnoDB
        """
    )
    cursor.execute(
        f"""
        INSERT INTO `{temp_table}` (event_id)
        SELECT `{id_column}`
        FROM (
            SELECT
                `{id_column}`,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        station_id,
                        trip_id,
                        `{columns["planned_date"]}`,
                        `{columns["planned_time"]}`
                    ORDER BY `{id_column}` DESC
                ) AS snapshot_rank
            FROM `{table}`
            WHERE trip_id IS NOT NULL
              AND trip_id <> ''
              AND `{columns["planned_date"]}` IS NOT NULL
              AND `{columns["planned_time"]}` IS NOT NULL
        ) AS ranked_snapshots
        WHERE snapshot_rank > 1
        """
    )
    selected = cursor.rowcount
    cursor.execute(
        f"""
        DELETE target
        FROM `{table}` AS target
        JOIN `{temp_table}` AS obsolete
          ON obsolete.event_id = target.`{id_column}`
        """
    )
    deleted = cursor.rowcount
    cursor.execute(f"DROP TEMPORARY TABLE `{temp_table}`")
    if deleted != selected:
        raise RuntimeError(
            f"{table}: selected {selected} obsolete rows but deleted {deleted}"
        )
    return deleted


def optimize_tables(cursor):
    for table in ("arrivals", "departures", "logs", "scrape_runs"):
        print(f"Optimizing {table}")
        cursor.execute(f"OPTIMIZE TABLE `{table}`")
        cursor.fetchall()
        while cursor.nextset():
            cursor.fetchall()


def main():
    args = parse_args()
    if args.optimize and not args.apply:
        raise SystemExit("--optimize requires --apply")

    connection = mysql.connector.connect(**db_config())
    cursor = connection.cursor()
    try:
        counts = {
            table: obsolete_count(cursor, table, columns)
            for table, columns in EVENT_TABLES.items()
        }
        for table, count in counts.items():
            print(f"{table}: {count} obsolete snapshot rows")

        if not args.apply:
            print("Dry run only. Re-run with --apply after creating a database backup.")
            return

        for table, columns in EVENT_TABLES.items():
            deleted = delete_obsolete_snapshots(cursor, table, columns)
            connection.commit()
            print(f"{table}: deleted {deleted} obsolete snapshot rows")

        if args.optimize:
            optimize_tables(cursor)

        print("TrainDB compaction completed.")
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
