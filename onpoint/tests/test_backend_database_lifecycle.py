import datetime
import unittest
from unittest.mock import patch

import backend


class FakeCursor:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self):
        self.created_cursor = FakeCursor()
        self.closed = False

    def cursor(self):
        return self.created_cursor

    def close(self):
        self.closed = True


class BackendDatabaseLifecycleTests(unittest.TestCase):
    def test_each_analysis_closes_its_database_session(self):
        departure = datetime.datetime(2026, 7, 17, 12, 0)
        arrival = departure + datetime.timedelta(hours=1)
        journey = {
            "duration": arrival - departure,
            "legs": [
                {
                    "origin": "Lingen(Ems)",
                    "origin_id": "1",
                    "destination": "Rheine",
                    "destination_id": "2",
                    "departure": departure,
                    "arrival": arrival,
                    "name": "RE 15",
                    "match_name": "RE 15",
                }
            ],
        }
        connection = FakeConnection()

        with (
            patch.object(
                backend,
                "fetch_live_journeys",
                return_value=([journey], "dbnav"),
            ),
            patch.object(
                backend.mysql.connector,
                "connect",
                return_value=connection,
            ) as connect,
        ):
            result = backend.run_analysis(
                {
                    "starting_location": "Lingen(Ems)",
                    "end_location": "Rheine",
                    "time": "2026-07-17T12:00",
                    "only_regionalverkehr": True,
                }
            )

        connect.assert_called_once_with(**backend.db_config())
        self.assertTrue(connection.created_cursor.closed)
        self.assertTrue(connection.closed)
        self.assertEqual(result["sum_tracked_trains"], 0)
        self.assertEqual(len(result["journeys"]), 1)


if __name__ == "__main__":
    unittest.main()
