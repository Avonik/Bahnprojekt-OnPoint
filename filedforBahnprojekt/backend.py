from flask import Flask, request, jsonify
from flask_cors import CORS
from pyhafas import HafasClient
from pyhafas.profile import VSNProfile, DBProfile
import datetime
from flask import Flask, render_template, request, jsonify
import datetime
from pyhafas import HafasClient
from pyhafas.profile import DBProfile
import mysql.connector
import os
import json
import re
import requests
import subprocess
from zoneinfo import ZoneInfo

from connection_model import estimate_connection

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def load_local_env(path):
    if load_dotenv:
        load_dotenv(path)
        return

    if not os.path.exists(path):
        return

    with open(path, encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value


load_local_env(os.path.join(os.path.dirname(__file__), ".env"))

app = Flask(__name__)
CORS(app)  # Enables CORS to allow cross-origin requestsp
client = HafasClient(DBProfile())
ROUTING_PROVIDER = os.getenv("ROUTING_PROVIDER", "auto").lower()
TRANSPORT_REST_BASE_URL = os.getenv("TRANSPORT_REST_BASE_URL", "https://v6.db.transport.rest")
NODE_EXECUTABLE = os.getenv("NODE_EXECUTABLE", "node")
DBWEB_ROUTE_PROVIDER_SCRIPT = os.path.join(os.path.dirname(__file__), "my-app", "dbweb_route_provider.mjs")
TRANSFER_COMFORT_PENALTY_MINUTES = float(os.getenv("TRANSFER_COMFORT_PENALTY_MINUTES", "5"))
DEFAULT_FALLBACK_DELAY_MINUTES = float(os.getenv("DEFAULT_FALLBACK_DELAY_MINUTES", "120"))


def db_config():
    return {
        "host": os.getenv("TRAINDB_HOST", "localhost"),
        "port": int(os.getenv("TRAINDB_PORT", "3306")),
        "user": os.getenv("TRAINDB_USER", "bahnapp"),
        "password": os.getenv("TRAINDB_PASSWORD", ""),
        "database": os.getenv("TRAINDB_DATABASE", "TrainDB"),
    }


db = mysql.connector.connect(**db_config())
cursor = db.cursor()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    data = request.get_json()  # Parses JSON data from the request body
    print('Received data:', data)  # Logs the received data to the server console
    try:
        result = run_analysis(data)
    except Exception as error:
        print('Route analysis failed:', error)
        return jsonify({"error": str(error)}), 500

    return jsonify({"journeys": result})  # Returns a JSON response


def run_analysis(data):
    time_input = data['time']
    sumTrains = 0

    time_obj = datetime.datetime.strptime(time_input, '%Y-%m-%dT%H:%M')

    only_regional = data.get("only_regionalverkehr", False)
    if(only_regional):
        includeThem = False
    else:
        includeThem = True

    resultJSON = {
        "journeys": []
    }

    best_score = float("inf")
    best_journey_index = -1
    fallback_cache = {}

    journeys = fetch_live_journeys(
        data['starting_location'],
        data['end_location'],
        time_obj,
        includeThem
    )

    #print(journeys)

    for idx, journey in enumerate(journeys):
        last_exp_arrival = None
        connection_success_product = 1.0
        risk_cost_minutes = 0.0
        transfer_penalty_minutes = 0.0
        duration_minutes = journey["duration"].total_seconds() / 60
        final_arrival_time = journey["legs"][-1]["arrival"]

        journey_data = {
            "duration": str(journey["duration"]),
            "scheduled_duration_minutes": round(duration_minutes, 1),
            "legs": [],
            "odds_of_successful_journey": 100,
            "risk_cost_minutes": 0,
            "transfer_penalty_minutes": 0,
            "expected_total_cost_minutes": round(duration_minutes, 1),
        }

        for leg in journey["legs"]:
            origin_station = leg["origin"]
            departure_time = leg["departure"]
            arrival_time = leg["arrival"]
            train = leg["name"]
            train_lookup_name = leg.get("match_name", train)
            departure_time_formatted = format_time(departure_time)
            arrival_time_formatted = format_time(arrival_time)

            if last_exp_arrival is not None:
                all_last_arrival_delays = get_all_arrival_delays(cursor, last_train_lookup_name, origin_station)
                all_next_departure_delays = get_all_departure_delays(cursor, train_lookup_name, origin_station)
                planned_layover_minutes = (departure_time - last_plan_arrival).total_seconds() / 60
                connection_estimate = estimate_connection(
                    all_last_arrival_delays,
                    all_next_departure_delays,
                    planned_layover_minutes,
                )
                expected_arrival_dt = add_delay_to_time(
                    last_plan_arrival,
                    connection_estimate.expected_arrival_delay_minutes,
                )
                expected_departure_dt = add_delay_to_time(
                    departure_time,
                    connection_estimate.expected_departure_delay_minutes,
                )
                fallback_start_time = estimate_fallback_start_time(
                    last_plan_arrival,
                    departure_time,
                    connection_estimate,
                )
                fallback_route = find_fallback_route(
                    origin_station,
                    data['end_location'],
                    fallback_start_time,
                    final_arrival_time,
                    includeThem,
                    train_lookup_name,
                    departure_time,
                    fallback_cache,
                )
                fallback_delay_minutes = (
                    fallback_route["extra_minutes"]
                    if fallback_route
                    else DEFAULT_FALLBACK_DELAY_MINUTES
                )
                connection_risk_cost_minutes = (
                    connection_estimate.failure_probability * fallback_delay_minutes
                )
                transfer_penalty_minutes += TRANSFER_COMFORT_PENALTY_MINUTES
                risk_cost_minutes += connection_risk_cost_minutes
                connection_success_product *= connection_estimate.success_probability

                sumTrains += (
                    connection_estimate.arrival_samples
                    + connection_estimate.departure_samples
                )

                leg_data = {
                    "layover_at": origin_station,
                    "layover_feasible": expected_arrival_dt <= expected_departure_dt,
                    "planned_layover_minutes": round(planned_layover_minutes, 1),
                    "planned_arrival": last_arrival_time_formatted,
                    "planned_departure": departure_time_formatted,
                    "expected_arrival": format_time(expected_arrival_dt),
                    "expected_departure": format_time(expected_departure_dt),
                    "last_train": last_train,
                    "last_train_average_arrival_delay": round(connection_estimate.expected_arrival_delay_minutes, 2),
                    "last_train_tracked": connection_estimate.arrival_samples,
                    "next_train": train,
                    "next_train_average_departure_delay": round(connection_estimate.expected_departure_delay_minutes, 2),
                    "next_train_tracked": connection_estimate.departure_samples,
                    "arrival_at_next_station": arrival_time_formatted,
                    "connection_success_probability": round(connection_estimate.success_probability * 100, 2),
                    "raw_connection_success_probability": round(connection_estimate.raw_success_probability * 100, 2),
                    "connection_failure_probability": round(connection_estimate.failure_probability * 100, 2),
                    "connection_risk_cost_minutes": round(connection_risk_cost_minutes, 1),
                    "fallback_delay_minutes": round(fallback_delay_minutes, 1),
                    "fallback_search_time": format_time(fallback_start_time),
                    "fallback_route": fallback_route,
                    "simulation": {
                        "method": connection_estimate.method,
                        "simulated_cases": connection_estimate.simulated_cases,
                        "effective_sample_size": round(connection_estimate.effective_sample_size, 1),
                        "expected_miss_lateness_minutes": round(connection_estimate.expected_miss_lateness_minutes, 1),
                    },
                }

                journey_data["legs"].append(leg_data)

            else:
                journey_data["start_train"] = train
                journey_data["start_time"] = departure_time_formatted

            last_exp_arrival = True
            last_plan_arrival = arrival_time
            last_arrival_time_formatted = arrival_time_formatted
            last_train = train
            last_train_lookup_name = train_lookup_name
            last_station = origin_station

        journey_data["odds_of_successful_journey"] = round(float(connection_success_product * 100), 2)
        journey_data["risk_cost_minutes"] = round(risk_cost_minutes, 1)
        journey_data["transfer_penalty_minutes"] = round(transfer_penalty_minutes, 1)
        journey_data["expected_total_cost_minutes"] = round(
            duration_minutes + transfer_penalty_minutes + risk_cost_minutes,
            1,
        )

        score = journey_data["expected_total_cost_minutes"]

        if score < best_score:
            best_score = score
            best_journey_index = idx

        #print(journey_data)
        #Wenn es Umstiege gibt ist die Ankunft nach dem letzten Umstieg die Ankunftszeit, sonst ist leg leer und einfach die ankunftszeit ist die ankunftszeit (lol)
        if journey_data["legs"]:
            journey_data["end_time"] = journey_data["legs"][-1]["arrival_at_next_station"]
        else:
            journey_data["end_time"] = arrival_time_formatted
        resultJSON["journeys"].append(journey_data)

        resultJSON["sum_tracked_trains"] = sumTrains


    # Mark the best journey
    if best_journey_index >= 0:
        resultJSON["journeys"][best_journey_index]["best_journey"] = True



    return resultJSON


def fetch_live_journeys(starting_location, end_location, time_obj, include_long_distance):
    provider = ROUTING_PROVIDER
    errors = []

    if provider in ("auto", "pyhafas"):
        try:
            print("Trying pyhafas route provider")
            return fetch_pyhafas_journeys(starting_location, end_location, time_obj, include_long_distance)
        except Exception as error:
            errors.append(f"pyhafas: {error}")
            print(f"pyhafas route provider failed: {error}")
            if provider == "pyhafas":
                raise

    if provider in ("auto", "dbweb", "db_vendo", "db-vendo"):
        try:
            print("Trying DB web route provider")
            return fetch_dbweb_journeys(starting_location, end_location, time_obj, include_long_distance)
        except Exception as error:
            errors.append(f"dbweb: {error}")
            print(f"DB web route provider failed: {error}")
            if provider in ("dbweb", "db_vendo", "db-vendo"):
                raise

    if provider in ("auto", "transport_rest", "transport.rest"):
        try:
            print("Trying transport.rest route provider")
            return fetch_transport_rest_journeys(starting_location, end_location, time_obj, include_long_distance)
        except Exception as error:
            errors.append(f"transport.rest: {error}")
            print(f"transport.rest route provider failed: {error}")
            if provider in ("transport_rest", "transport.rest"):
                raise

    raise RuntimeError("No route provider worked. " + " | ".join(errors))


def max_datetime(first, second):
    if first is None:
        return second
    if second is None:
        return first
    return first if first >= second else second


def estimate_fallback_start_time(planned_arrival, planned_departure, connection_estimate):
    if connection_estimate.conditional_missed_arrival_delay_minutes is not None:
        missed_arrival = add_delay_to_time(
            planned_arrival,
            connection_estimate.conditional_missed_arrival_delay_minutes,
        )
    else:
        missed_arrival = None

    if connection_estimate.conditional_missed_departure_delay_minutes is not None:
        missed_departure = add_delay_to_time(
            planned_departure,
            connection_estimate.conditional_missed_departure_delay_minutes,
        )
    else:
        missed_departure = planned_departure

    return max_datetime(
        missed_departure + datetime.timedelta(minutes=1),
        missed_arrival,
    )


def find_fallback_route(
    starting_location,
    end_location,
    time_obj,
    original_arrival,
    include_long_distance,
    missed_train,
    missed_departure,
    cache,
):
    if starting_location == end_location:
        return None

    cache_key = (
        starting_location,
        end_location,
        time_obj.isoformat(timespec="minutes"),
        include_long_distance,
        missed_train,
        missed_departure.isoformat(timespec="minutes"),
    )

    if cache_key in cache:
        return cache[cache_key]

    try:
        fallback_journeys = fetch_live_journeys(
            starting_location,
            end_location,
            time_obj,
            include_long_distance,
        )
    except Exception as error:
        print(f'Fallback route lookup skipped for {starting_location} -> {end_location}: {error}')
        cache[cache_key] = None
        return None

    usable_journeys = [
        journey for journey in fallback_journeys
        if is_usable_fallback_journey(journey, time_obj, missed_train, missed_departure)
    ]

    if not usable_journeys:
        cache[cache_key] = None
        return None

    best = min(usable_journeys, key=lambda journey: journey["legs"][-1]["arrival"])
    first_leg = best["legs"][0]
    last_leg = best["legs"][-1]
    arrival = last_leg["arrival"]
    extra_minutes = max(0.0, (arrival - original_arrival).total_seconds() / 60)

    fallback = {
        "from": starting_location,
        "to": end_location,
        "search_time": format_time(time_obj),
        "departure_time": format_time(first_leg["departure"]),
        "arrival_time": format_time(arrival),
        "duration": str(best["duration"]),
        "transfers": max(0, len(best["legs"]) - 1),
        "start_train": first_leg["name"],
        "extra_minutes": round(extra_minutes, 1),
        "legs": [
            {
                "train": leg["name"],
                "origin": leg["origin"],
                "destination": leg["destination"],
                "departure": format_time(leg["departure"]),
                "arrival": format_time(leg["arrival"]),
            }
            for leg in best["legs"]
        ],
    }

    cache[cache_key] = fallback
    return fallback


def is_usable_fallback_journey(journey, earliest_departure, missed_train, missed_departure):
    if not journey.get("legs"):
        return False

    first_leg = journey["legs"][0]
    last_leg = journey["legs"][-1]
    first_departure = first_leg.get("departure")

    if not first_departure or not last_leg.get("arrival"):
        return False

    if first_departure < earliest_departure:
        return False

    same_missed_train = first_leg.get("name") == missed_train
    same_or_earlier_departure = first_departure <= missed_departure

    return not (same_missed_train and same_or_earlier_departure)


def fetch_dbweb_journeys(starting_location, end_location, time_obj, include_long_distance):
    departure_time = format_local_departure_time(time_obj)
    command = [
        NODE_EXECUTABLE,
        DBWEB_ROUTE_PROVIDER_SCRIPT,
        starting_location,
        end_location,
        departure_time,
        str(include_long_distance).lower(),
    ]

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=45,
        check=False,
    )

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(detail or f"DB web provider exited with code {completed.returncode}")

    payload = json.loads(completed.stdout)
    normalized_journeys = []

    for journey in payload.get("journeys", []):
        normalized_legs = []
        for leg in journey.get("legs", []):
            departure = parse_dbweb_time(leg.get("departure"))
            arrival = parse_dbweb_time(leg.get("arrival"))

            if not leg.get("name") or not departure or not arrival:
                continue

            normalized_legs.append({
                "origin": leg.get("origin", "N/A"),
                "destination": leg.get("destination", "N/A"),
                "departure": departure,
                "arrival": arrival,
                "name": leg["name"],
                "match_name": leg.get("match_name", leg["name"]),
            })

        if not normalized_legs:
            continue

        duration = normalized_legs[-1]["arrival"] - normalized_legs[0]["departure"]
        normalized_journeys.append({
            "duration": duration,
            "legs": normalized_legs,
        })

    return normalized_journeys


def fetch_pyhafas_journeys(starting_location, end_location, time_obj, include_long_distance):
    start = client.locations(starting_location)[0]
    finish = client.locations(end_location)[0]

    journeys = client.journeys(
        origin=start,
        destination=finish,
        date=time_obj,
        max_changes=10,
        min_change_time=5,
        max_journeys=10,
        products={
            'long_distance_express': include_long_distance,
            "long_distance": include_long_distance,
            'regional_express': True,
            'regional': True,
            "suburban": True,
        }
    )

    normalized_journeys = []
    for journey in journeys:
        detailed_journey = client.journey(journey.id)
        normalized_legs = []

        for leg in detailed_journey.legs:
            try:
                if leg.mode == leg.mode.WALKING:
                    continue
            except AttributeError:
                pass

            normalized_legs.append({
                "origin": leg.origin.name,
                "destination": leg.destination.name,
                "departure": leg.departure,
                "arrival": leg.arrival,
                "name": leg.name,
                "match_name": leg.name,
            })

        if normalized_legs:
            normalized_journeys.append({
                "duration": detailed_journey.duration,
                "legs": normalized_legs,
            })

    return normalized_journeys


def fetch_transport_rest_journeys(starting_location, end_location, time_obj, include_long_distance):
    start = find_transport_rest_location(starting_location)
    finish = find_transport_rest_location(end_location)
    departure_time = format_departure_time_with_optional_timezone(time_obj)

    response = requests.get(
        f"{TRANSPORT_REST_BASE_URL}/journeys",
        params={
            "from": start["id"],
            "to": finish["id"],
            "departure": departure_time,
            "results": 10,
            "transfers": 10,
            "transferTime": 5,
            "stopovers": "false",
            "nationalExpress": str(include_long_distance).lower(),
            "national": str(include_long_distance).lower(),
            "regionalExpress": "true",
            "regional": "true",
            "suburban": "true",
            "bus": "false",
            "ferry": "false",
            "subway": "false",
            "tram": "false",
            "taxi": "false",
            "language": "de",
        },
        headers={"User-Agent": "BahnProjekt local dev"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    normalized_journeys = []

    for journey in payload.get("journeys", []):
        normalized_legs = []
        for leg in journey.get("legs", []):
            line = leg.get("line") or {}
            train_name = line.get("name") or leg.get("tripId")
            departure = parse_transport_rest_time(leg.get("plannedDeparture") or leg.get("departure"))
            arrival = parse_transport_rest_time(leg.get("plannedArrival") or leg.get("arrival"))

            if not train_name or not departure or not arrival:
                continue

            normalized_legs.append({
                "origin": (leg.get("origin") or {}).get("name", "N/A"),
                "destination": (leg.get("destination") or {}).get("name", "N/A"),
                "departure": departure,
                "arrival": arrival,
                "name": train_name,
                "match_name": train_name,
            })

        if not normalized_legs:
            continue

        duration = normalized_legs[-1]["arrival"] - normalized_legs[0]["departure"]
        normalized_journeys.append({
            "duration": duration,
            "legs": normalized_legs,
        })

    return normalized_journeys


def find_transport_rest_location(query):
    response = requests.get(
        f"{TRANSPORT_REST_BASE_URL}/locations",
        params={
            "query": query,
            "results": 1,
            "stops": "true",
            "addresses": "false",
            "poi": "false",
            "language": "de",
        },
        headers={"User-Agent": "BahnProjekt local dev"},
        timeout=15,
    )
    response.raise_for_status()
    locations = response.json()

    if not locations:
        raise RuntimeError(f"No station found for {query}")

    return locations[0]


def parse_transport_rest_time(value):
    if not value:
        return None

    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))


def format_local_departure_time(time_obj):
    return time_obj.isoformat(timespec="seconds")


def format_departure_time_with_optional_timezone(time_obj):
    try:
        return time_obj.replace(tzinfo=ZoneInfo("Europe/Berlin")).isoformat()
    except Exception:
        return format_local_departure_time(time_obj)


def parse_dbweb_time(value):
    if not value:
        return None

    return datetime.datetime.fromisoformat(value)


def calculate_travel_time(departure_time, arrival_time):
    if departure_time and arrival_time:
        travel_duration = arrival_time - departure_time
        hours, remainder = divmod(travel_duration.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{int(hours)}h {int(minutes)}m" if hours > 0 else f"{int(minutes)}m"
    else:
        return "N/A"

def format_time(time_obj):
    return time_obj.strftime("%H:%M") if time_obj else "N/A"

def add_delay_to_time(planned_time, delay_minutes):
    if planned_time and delay_minutes is not None:
        return planned_time + datetime.timedelta(minutes=float(delay_minutes))
    return planned_time

def to_float(value, default=0):
    if value is None:
        return default

    return float(value)

def train_name_filter(train):
    train_number_match = re.search(r"(\d+)\s*$", train or "")
    if train_number_match and len(train_number_match.group(1)) >= 3:
        return "(trains.train_name = %s OR trains.train_name REGEXP %s)", [
            train,
            f"(^|[^0-9]){train_number_match.group(1)}$",
        ]

    return "trains.train_name = %s", [train]

def get_all_arrival_delays(cursor, train, station):
    train_filter, train_params = train_name_filter(train)
    query = """
        WITH RankedArrivals AS (
        SELECT
            arrivals.*,
            stations.station_name,
            trains.train_name,
            ROW_NUMBER() OVER (PARTITION BY arrivals.trip_id ORDER BY arrivals.arrival_id DESC) AS rn
        FROM arrivals
        JOIN stations ON arrivals.station_id = stations.station_id
        JOIN trains ON arrivals.train_id = trains.train_id
        WHERE """ + train_filter + """
          AND stations.station_name = %s
          AND arrivals.trip_id IS NOT NULL
          AND arrivals.trip_id <> ''
        )
        SELECT delay_minutes
        FROM RankedArrivals
        WHERE rn = 1;
    """
    try:
        cursor.execute(query, train_params + [station])
        return cursor.fetchall()
    except mysql.connector.Error as error:
        print(f'Arrival delay lookup skipped for {train} at {station}: {error}')
        return []

def get_all_departure_delays(cursor, train, station):
    train_filter, train_params = train_name_filter(train)
    query = """
        WITH RankedDepartures AS (
    SELECT
        departures.*,
        stations.station_name,
        trains.train_name,
        ROW_NUMBER() OVER (PARTITION BY departures.trip_id ORDER BY departures.departure_id DESC) AS rn
    FROM departures
    JOIN stations ON departures.station_id = stations.station_id
    JOIN trains ON departures.train_id = trains.train_id
    WHERE """ + train_filter + """
      AND stations.station_name = %s
      AND departures.trip_id IS NOT NULL
      AND departures.trip_id <> ''
    )
    SELECT delay_minutes
    FROM RankedDepartures
    WHERE rn = 1;
    """
    try:
        cursor.execute(query, train_params + [station])
        return cursor.fetchall()
    except mysql.connector.Error as error:
        print(f'Departure delay lookup skipped for {train} at {station}: {error}')
        return []

def grab_EV_arrival(train, station, last_plan_arrival):
    average_arrival_delay = 0
    train_tracked = 0
    expected_arrival_formatted = format_time(last_plan_arrival)
    train_filter, train_params = train_name_filter(train)
    query = """
        WITH RankedArrivals AS (
        SELECT
            arrivals.*,
            stations.station_name,
            trains.train_name,
            ROW_NUMBER() OVER (PARTITION BY arrivals.trip_id ORDER BY arrivals.arrival_id DESC) AS rn
        FROM arrivals
        JOIN stations ON arrivals.station_id = stations.station_id
        JOIN trains ON arrivals.train_id = trains.train_id
        WHERE """ + train_filter + """
          AND stations.station_name = %s
          AND arrivals.trip_id IS NOT NULL
          AND arrivals.trip_id <> ''
        )
        SELECT AVG(delay_minutes), Count(*)
        FROM RankedArrivals
        WHERE rn = 1;
    """
    try:
        cursor.execute(query, train_params + [station])
        result = cursor.fetchall()
    except mysql.connector.Error as error:
        print(f'Expected arrival lookup skipped for {train} at {station}: {error}')
        return train_tracked, expected_arrival_formatted, average_arrival_delay

    if result:
        average_arrival_delay = to_float(result[0][0])
        train_tracked = result[0][1]
        expected_arrival = add_delay_to_time(last_plan_arrival, average_arrival_delay)
        expected_arrival_formatted = format_time(expected_arrival)
    return train_tracked, expected_arrival_formatted, average_arrival_delay

def grab_EV_departure(train, station, departure_time):
    average_departure_delay = 0
    train_tracked = 0
    expected_departure_formatted = format_time(departure_time)
    train_filter, train_params = train_name_filter(train)
    query = """
        WITH RankedDepartures AS (
            SELECT
                departures.*,
                stations.station_name,
                trains.train_name,
                ROW_NUMBER() OVER (PARTITION BY departures.trip_id ORDER BY departures.departure_id DESC) AS rn
            FROM departures
            JOIN stations ON departures.station_id = stations.station_id
            JOIN trains ON departures.train_id = trains.train_id
            WHERE """ + train_filter + """
              AND stations.station_name = %s
              AND departures.trip_id IS NOT NULL
              AND departures.trip_id <> ''
        )
        SELECT AVG(delay_minutes), Count(*)
        FROM RankedDepartures
        WHERE rn = 1;
    """
    try:
        cursor.execute(query, train_params + [station])
        result = cursor.fetchall()
    except mysql.connector.Error as error:
        print(f'Expected departure lookup skipped for {train} at {station}: {error}')
        return train_tracked, expected_departure_formatted, average_departure_delay

    if result:
        average_departure_delay = to_float(result[0][0])
        train_tracked = result[0][1]
        expected_departure = add_delay_to_time(departure_time, average_departure_delay)
        expected_departure_formatted = format_time(expected_departure)
    return train_tracked, expected_departure_formatted, average_departure_delay

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  # Starts the server on localhost:5000
