import unittest

from connection_model import estimate_connection


class ConnectionModelCancellationTests(unittest.TestCase):
    def test_cancellation_reduces_connection_probability(self):
        without_cancellation = estimate_connection(
            [(0, False), (0, False)],
            [(0, False), (0, False)],
            scheduled_layover_minutes=5,
        )
        with_cancellation = estimate_connection(
            [(0, False), (0, True)],
            [(0, False), (0, False)],
            scheduled_layover_minutes=5,
        )

        self.assertLess(
            with_cancellation.success_probability,
            without_cancellation.success_probability,
        )
        self.assertEqual(with_cancellation.arrival_cancellations, 1)
        self.assertEqual(with_cancellation.departure_cancellations, 0)
        self.assertAlmostEqual(
            with_cancellation.arrival_cancellation_probability,
            0.5,
        )


if __name__ == "__main__":
    unittest.main()
