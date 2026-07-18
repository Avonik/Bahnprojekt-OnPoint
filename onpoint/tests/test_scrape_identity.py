import datetime as dt
import unittest

from scrape_train_data import event_key


class EventIdentityTests(unittest.TestCase):
    def test_same_trip_at_different_planned_times_stays_separate(self):
        first_run = event_key(
            "departure",
            42,
            "provider-trip-id",
            dt.datetime(2026, 7, 16, 8, 0),
        )
        second_run = event_key(
            "departure",
            42,
            "provider-trip-id",
            dt.datetime(2026, 7, 16, 10, 0),
        )

        self.assertNotEqual(first_run, second_run)

    def test_repeated_observation_of_same_event_has_same_key(self):
        planned = dt.datetime(2026, 7, 16, 8, 0)
        first_observation = event_key(
            "arrival",
            42,
            "provider-trip-id",
            planned,
        )
        later_observation = event_key(
            "arrival",
            42,
            "provider-trip-id",
            planned,
        )

        self.assertEqual(first_observation, later_observation)


if __name__ == "__main__":
    unittest.main()
