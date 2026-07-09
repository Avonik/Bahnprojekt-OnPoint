import {createClient} from 'db-vendo-client';
import {profile as dbwebProfile} from 'db-vendo-client/p/dbweb/index.js';

const [
	stationQuery,
	boardMode = 'both',
	whenIso = new Date().toISOString(),
	durationArg = '60',
	resultsArg = '80',
] = process.argv.slice(2);

if (!stationQuery) {
	console.error('Usage: node dbweb_station_board.mjs <station> [both|departures|arrivals] [whenIso] [durationMinutes] [results]');
	process.exit(2);
}

const duration = Number.parseInt(durationArg, 10);
const results = Number.parseInt(resultsArg, 10);
const userAgent = process.env.DBWEB_USER_AGENT ||
	'Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';
const client = createClient(dbwebProfile, userAgent, {enrichStations: true});

const findStation = async (query) => {
	const locations = await client.locations(query, {
		results: 1,
		stops: true,
		addresses: false,
		poi: false,
	});

	if (!locations?.[0]) {
		throw new Error(`No station found for ${query}`);
	}

	return locations[0];
};

const isRailService = (entry) => {
	const line = entry.line || {};
	const product = line.product || '';
	const name = line.name || '';

	if (line.mode === 'train') return true;
	if (['nationalExpress', 'national', 'regionalExp', 'regional', 'suburban'].includes(product)) return true;
	return /^(ICE|IC|EC|RE|RB|S|IRE|NJ|EN)\b/i.test(name);
};

const parseDelayMinutes = (entry) => {
	if (typeof entry.delay === 'number') {
		return Math.round(entry.delay / 60);
	}

	if (entry.when && entry.plannedWhen) {
		const actual = Date.parse(entry.when);
		const planned = Date.parse(entry.plannedWhen);

		if (!Number.isNaN(actual) && !Number.isNaN(planned)) {
			return Math.round((actual - planned) / 60000);
		}
	}

	return 0;
};

const normalizeBoardEntry = (entry, type, fallbackStation) => {
	if (entry.cancelled || !isRailService(entry)) {
		return null;
	}

	const plannedWhen = entry.plannedWhen || entry.when;
	const actualWhen = entry.when || entry.plannedWhen;
	const line = entry.line || {};
	const trainName = line.name || line.fahrtNr || String(entry.trip || '');

	if (!plannedWhen || !actualWhen || !trainName) {
		return null;
	}

	return {
		type,
		trip_id: entry.tripId || `${trainName}-${plannedWhen}`,
		train_name: trainName,
		train_direction: entry.direction || entry.destination?.name || '',
		station_name: entry.stop?.name || fallbackStation.name,
		station_id: entry.stop?.id || fallbackStation.id,
		latitude: entry.stop?.location?.latitude || fallbackStation.location?.latitude || fallbackStation.latitude || null,
		longitude: entry.stop?.location?.longitude || fallbackStation.location?.longitude || fallbackStation.longitude || null,
		planned_time: plannedWhen,
		actual_time: actualWhen,
		delay_minutes: parseDelayMinutes(entry),
	};
};

const fetchBoard = async (station, type) => {
	const method = type === 'arrivals' ? client.arrivals.bind(client) : client.departures.bind(client);
	const payload = await method(station.id, {
		when: new Date(whenIso),
		duration,
		results,
		stopovers: false,
		remarks: false,
		includeRelatedStations: false,
	});

	return (payload[type] || [])
		.map((entry) => normalizeBoardEntry(entry, type.slice(0, -1), station))
		.filter(Boolean);
};

const station = await findStation(stationQuery);
const boards = [];

if (boardMode === 'both' || boardMode === 'departures') {
	boards.push(...await fetchBoard(station, 'departures'));
}

if (boardMode === 'both' || boardMode === 'arrivals') {
	boards.push(...await fetchBoard(station, 'arrivals'));
}

console.log(JSON.stringify({
	station: {
		id: station.id,
		name: station.name,
		latitude: station.location?.latitude || station.latitude || null,
		longitude: station.location?.longitude || station.longitude || null,
	},
	events: boards,
}));
