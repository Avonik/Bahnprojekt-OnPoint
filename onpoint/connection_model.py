from dataclasses import dataclass
from itertools import product
from statistics import mean


DEFAULT_PRIOR_SUCCESS_PROBABILITY = 0.85
DEFAULT_SMOOTHING_STRENGTH = 8.0
MAX_EXACT_COMBINATIONS = 250000


@dataclass
class ConnectionEstimate:
    success_probability: float
    raw_success_probability: float
    failure_probability: float
    expected_arrival_delay_minutes: float
    expected_departure_delay_minutes: float
    conditional_missed_arrival_delay_minutes: float | None
    conditional_missed_departure_delay_minutes: float | None
    expected_miss_lateness_minutes: float
    effective_sample_size: float
    arrival_samples: int
    departure_samples: int
    arrival_cancellations: int
    departure_cancellations: int
    arrival_cancellation_probability: float
    departure_cancellation_probability: float
    simulated_cases: int
    method: str


def normalize_delay_rows(rows):
    delays = []
    cancellations = 0
    samples = 0

    for row in rows or []:
        if isinstance(row, (tuple, list)):
            value = row[0] if row else None
            cancelled = bool(row[1]) if len(row) > 1 else False
        else:
            value = row
            cancelled = False

        samples += 1
        if cancelled:
            cancellations += 1
            continue
        if value is None:
            continue
        delays.append(float(value))

    return {
        "delays": delays,
        "cancellations": cancellations,
        "samples": samples,
        "cancellation_probability": cancellations / samples if samples else 0.0,
    }


def expected_delay(delays):
    return mean(delays) if delays else 0.0


def empirical_success_probability(arrival_delays, departure_delays, scheduled_layover_minutes):
    arrivals = arrival_delays or [0.0]
    departures = departure_delays or [0.0]
    total_combinations = len(arrivals) * len(departures)

    if total_combinations <= MAX_EXACT_COMBINATIONS:
        successful = 0
        missed_arrival_delays = []
        missed_departure_delays = []
        miss_lateness_values = []

        for arrival_delay, departure_delay in product(arrivals, departures):
            margin = scheduled_layover_minutes + departure_delay - arrival_delay
            if margin >= 0:
                successful += 1
            else:
                missed_arrival_delays.append(arrival_delay)
                missed_departure_delays.append(departure_delay)
                miss_lateness_values.append(-margin)

        return {
            "raw_probability": successful / total_combinations,
            "simulated_cases": total_combinations,
            "method": "exact_empirical",
            "missed_arrival_delay": mean(missed_arrival_delays) if missed_arrival_delays else None,
            "missed_departure_delay": mean(missed_departure_delays) if missed_departure_delays else None,
            "miss_lateness": mean(miss_lateness_values) if miss_lateness_values else 0.0,
        }

    arrivals_sorted = sorted(arrivals)
    successful = 0

    for departure_delay in departures:
        threshold = scheduled_layover_minutes + departure_delay
        successful += count_less_or_equal(arrivals_sorted, threshold)

    return {
        "raw_probability": successful / total_combinations,
        "simulated_cases": total_combinations,
        "method": "exact_empirical_sorted",
        "missed_arrival_delay": None,
        "missed_departure_delay": None,
        "miss_lateness": 0.0,
    }


def count_less_or_equal(values, threshold):
    left = 0
    right = len(values)

    while left < right:
        mid = (left + right) // 2
        if values[mid] <= threshold:
            left = mid + 1
        else:
            right = mid

    return left


def effective_sample_size(arrival_count, departure_count):
    if arrival_count and departure_count:
        return float(min(arrival_count, departure_count))
    if arrival_count or departure_count:
        return float(max(arrival_count, departure_count))
    return 0.0


def smooth_probability(raw_probability, sample_size, prior_probability, smoothing_strength):
    if sample_size <= 0:
        return prior_probability

    return (
        raw_probability * sample_size + prior_probability * smoothing_strength
    ) / (sample_size + smoothing_strength)


def estimate_connection(
    arrival_delay_rows,
    departure_delay_rows,
    scheduled_layover_minutes,
    prior_probability=DEFAULT_PRIOR_SUCCESS_PROBABILITY,
    smoothing_strength=DEFAULT_SMOOTHING_STRENGTH,
):
    arrival_data = normalize_delay_rows(arrival_delay_rows)
    departure_data = normalize_delay_rows(departure_delay_rows)
    arrival_delays = arrival_data["delays"]
    departure_delays = departure_data["delays"]
    empirical_result = empirical_success_probability(
        arrival_delays,
        departure_delays,
        scheduled_layover_minutes,
    )
    operating_probability = (
        (1.0 - arrival_data["cancellation_probability"])
        * (1.0 - departure_data["cancellation_probability"])
    )
    raw_probability = empirical_result["raw_probability"] * operating_probability
    sample_size = effective_sample_size(
        arrival_data["samples"],
        departure_data["samples"],
    )
    probability = smooth_probability(
        raw_probability,
        sample_size,
        prior_probability,
        smoothing_strength,
    )

    probability = min(1.0, max(0.0, probability))

    return ConnectionEstimate(
        success_probability=probability,
        raw_success_probability=raw_probability,
        failure_probability=1.0 - probability,
        expected_arrival_delay_minutes=expected_delay(arrival_delays),
        expected_departure_delay_minutes=expected_delay(departure_delays),
        conditional_missed_arrival_delay_minutes=empirical_result["missed_arrival_delay"],
        conditional_missed_departure_delay_minutes=empirical_result["missed_departure_delay"],
        expected_miss_lateness_minutes=empirical_result["miss_lateness"],
        effective_sample_size=sample_size,
        arrival_samples=arrival_data["samples"],
        departure_samples=departure_data["samples"],
        arrival_cancellations=arrival_data["cancellations"],
        departure_cancellations=departure_data["cancellations"],
        arrival_cancellation_probability=arrival_data["cancellation_probability"],
        departure_cancellation_probability=departure_data["cancellation_probability"],
        simulated_cases=empirical_result["simulated_cases"],
        method=(
            f"{empirical_result['method']}_with_cancellations"
            if arrival_data["cancellations"] or departure_data["cancellations"]
            else empirical_result["method"]
        ),
    )
