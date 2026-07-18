import {createClient} from 'db-vendo-client';
import {profile as dbProfile} from 'db-vendo-client/p/db/index.js';
import {profile as dbwebProfile} from 'db-vendo-client/p/dbweb/index.js';
import {profile as dbrisProfile} from 'db-vendo-client/p/dbris/index.js';
import {readSimplifiedStations} from 'db-hafas-stations';

const formatProviderError = (error) => {
	const status = error?.response?.status;
	const statusText = error?.response?.statusText;
	const url = error?.url || error?.response?.url;
	const message = error?.message || String(error);
	return [
		status ? `HTTP ${status}` : null,
		statusText && statusText !== message ? statusText : null,
		message,
		url ? `at ${url}` : null,
	].filter(Boolean).join(' ');
};

const exitWithProviderError = (error) => {
	console.error(formatProviderError(error));
	process.exit(1);
};

process.on('uncaughtException', exitWithProviderError);
process.on('unhandledRejection', exitWithProviderError);

const outputJson = (value) => process.stdout.write(`${JSON.stringify(value)}\n`);
console.log = (...values) => console.error(...values);

const args = process.argv.slice(2);
const batchMode = args[0] === '--batch';
const profileName = (process.env.STATION_BOARD_PROFILE || 'dbweb').toLowerCase();
const stationBoardProfile = profileName === 'dbris'
	? dbrisProfile
	: profileName === 'db'
		? dbProfile
		: dbwebProfile;

if (profileName === 'dbris' && (!process.env.DB_CLIENT_ID || !process.env.DB_API_KEY)) {
	throw new Error('STATION_BOARD_PROFILE=dbris requires DB_CLIENT_ID and DB_API_KEY from the DB API Marketplace.');
}

const userAgent = stationBoardProfile === dbwebProfile
	? (process.env.DBWEB_USER_AGENT ||
		'Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
	: (process.env.STATION_BOARD_USER_AGENT ||
		'OnPoint Bahnprojekt/1.0 (https://bahn.juhermes.de; https://juhermes.de)');
const client = createClient(stationBoardProfile, userAgent, {enrichStations: false});
const retryAttempts = Math.max(
	1,
	Number.parseInt(process.env.SCRAPE_RETRY_ATTEMPTS || '4', 10),
);
const stationPauseMs = Math.max(
	0,
	Number.parseInt(process.env.SCRAPE_STATION_PAUSE_MS || '750', 10),
);
const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

const retryableProviderError = (error) => {
	const status = error?.response?.status;
	if (status === 429 || (status >= 500 && status <= 599)) return true;
	return !status && /connect|network|socket|timeout|fetch/i.test(error?.message || '');
};

const withRetry = async (operation) => {
	let lastError;
	for (let attempt = 1; attempt <= retryAttempts; attempt += 1) {
		try {
			return await operation();
		} catch (error) {
			lastError = error;
			if (attempt >= retryAttempts || !retryableProviderError(error)) throw error;
			const backoffMs = Math.min(15000, 1500 * (2 ** (attempt - 1)));
			await sleep(backoffMs);
		}
	}
	throw lastError;
};

const normalizeStationName = (value) => String(value || '')
	.toLowerCase()
	.normalize('NFD')
	.replace(/[\u0300-\u036f]/g, '')
	.replace(/ß/g, 'ss')
	.replace(/[^a-z0-9]+/g, ' ')
	.trim();

let stationIndexPromise;
const loadStationIndex = () => {
	if (!stationIndexPromise) {
		stationIndexPromise = (async () => {
			const exact = new Map();
			const stations = [];
			for await (const station of readSimplifiedStations()) {
				const normalizedName = normalizeStationName(station.name);
				if (!exact.has(normalizedName)) exact.set(normalizedName, station);
				stations.push({normalizedName, station});
			}
			return {exact, stations};
		})();
	}
	return stationIndexPromise;
};

const stationCache = new Map();
const resolveStation = async (query) => {
	const normalizedQuery = normalizeStationName(query);
	const {exact, stations} = await loadStationIndex();
	const exactMatch = exact.get(normalizedQuery);
	if (exactMatch) return exactMatch;

	const hbfMatch = exact.get(`${normalizedQuery} hbf`);
	if (hbfMatch) return hbfMatch;

	const partialMatches = stations
		.filter(({normalizedName}) => normalizedName.includes(normalizedQuery))
		.sort((left, right) =>
			left.normalizedName.length - right.normalizedName.length
		);
	if (partialMatches[0]) return partialMatches[0].station;

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

const findStation = (query) => {
	const key = normalizeStationName(query);
	if (!stationCache.has(key)) stationCache.set(key, resolveStation(query));
	return stationCache.get(key);
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

const hasRealtimeInformation = (entry) => {
	if (entry.cancelled || typeof entry.delay === 'number') return true;
	if (!entry.when || !entry.plannedWhen) return false;

	const actual = Date.parse(entry.when);
	const planned = Date.parse(entry.plannedWhen);
	return !Number.isNaN(actual) && !Number.isNaN(planned) && actual !== planned;
};

const normalizeBoardEntry = (entry, type, fallbackStation, requestedStation) => {
	if (!isRailService(entry)) {
		return null;
	}

	const plannedWhen = entry.plannedWhen || entry.when;
	const actualWhen = entry.when || entry.plannedWhen;
	const line = entry.line || {};
	const trainName = line.name || line.fahrtNr || String(entry.tripId || entry.trip || '');

	if (!plannedWhen || !actualWhen || !trainName) {
		return null;
	}

	return {
		type,
		trip_id: entry.tripId || `${trainName}-${plannedWhen}`,
		train_name: trainName,
		train_direction: entry.direction || entry.destination?.name || '',
		station_name: entry.stop?.name || fallbackStation.name,
		station_id: String(entry.stop?.id || fallbackStation.id || ''),
		requested_station: requestedStation,
		latitude: entry.stop?.location?.latitude || fallbackStation.location?.latitude || fallbackStation.latitude || null,
		longitude: entry.stop?.location?.longitude || fallbackStation.location?.longitude || fallbackStation.longitude || null,
		planned_time: plannedWhen,
		actual_time: actualWhen,
		delay_minutes: parseDelayMinutes(entry),
		cancelled: Boolean(entry.cancelled),
		realtime_known: hasRealtimeInformation(entry),
	};
};

const fetchBoard = async (station, requestedStation, type, whenIso, duration, results) => {
	const method = type === 'arrivals' ? client.arrivals.bind(client) : client.departures.bind(client);
	const payload = await withRetry(() => method(station.id, {
		when: new Date(whenIso),
		duration,
		results,
		stopovers: false,
		remarks: false,
		includeRelatedStations: false,
	}));

	return (payload[type] || [])
		.map((entry) =>
			normalizeBoardEntry(entry, type.slice(0, -1), station, requestedStation)
		)
		.filter(Boolean);
};

const stationSummary = (station) => ({
	id: String(station.id || ''),
	name: station.name,
	latitude: station.location?.latitude || station.latitude || null,
	longitude: station.location?.longitude || station.longitude || null,
});

const fetchStationBoard = async ({
	station: stationQuery,
	mode = 'both',
	when = new Date().toISOString(),
	duration = 60,
	results = 80,
}) => {
	if (!stationQuery) throw new Error('Missing station query');

	const station = await findStation(stationQuery);
	const boardRequests = [];

	if (mode === 'both' || mode === 'departures') {
		boardRequests.push({
			type: 'departures',
			promise: fetchBoard(
				station,
				stationQuery,
				'departures',
				when,
				Number(duration),
				Number(results),
			),
		});
	}

	if (mode === 'both' || mode === 'arrivals') {
		boardRequests.push({
			type: 'arrivals',
			promise: fetchBoard(
				station,
				stationQuery,
				'arrivals',
				when,
				Number(duration),
				Number(results),
			),
		});
	}

	const settledBoards = await Promise.allSettled(
		boardRequests.map(({promise}) => promise),
	);
	const events = [];
	const errors = [];
	settledBoards.forEach((result, index) => {
		if (result.status === 'fulfilled') {
			events.push(...result.value);
		} else {
			errors.push(
				`${boardRequests[index].type}: ${formatProviderError(result.reason)}`,
			);
		}
	});

	if (!events.length && errors.length) {
		throw new Error(errors.join(' | '));
	}

	const response = {
		station: stationSummary(station),
		events,
	};
	if (errors.length) response.error = errors.join(' | ');
	return response;
};

const mapWithConcurrency = async (items, concurrency, mapper) => {
	const output = new Array(items.length);
	let nextIndex = 0;
	const worker = async () => {
		while (true) {
			const index = nextIndex++;
			if (index >= items.length) return;
			output[index] = await mapper(items[index], index);
			if (stationPauseMs > 0 && nextIndex < items.length) {
				await sleep(stationPauseMs);
			}
		}
	};
	await Promise.all(
		Array.from(
			{length: Math.min(concurrency, Math.max(1, items.length))},
			worker,
		),
	);
	return output;
};

const readStdin = async () => {
	let input = '';
	for await (const chunk of process.stdin) input += chunk;
	return input;
};

if (batchMode) {
	const concurrency = Math.max(1, Number.parseInt(args[1] || '3', 10));
	const payload = JSON.parse(await readStdin());
	const requests = Array.isArray(payload.requests) ? payload.requests : [];
	const responses = await mapWithConcurrency(requests, concurrency, async (request, index) => {
		try {
			return {
				id: request.id ?? index,
				query: request.station,
				...await fetchStationBoard(request),
			};
		} catch (error) {
			return {
				id: request.id ?? index,
				query: request.station,
				error: formatProviderError(error),
			};
		}
	});
	outputJson({responses});
} else {
	const [
		stationQuery,
		boardMode = 'both',
		whenIso = new Date().toISOString(),
		durationArg = '60',
		resultsArg = '80',
	] = args;

	if (!stationQuery) {
		console.error('Usage: bun dbweb_station_board.mjs <station> [both|departures|arrivals] [whenIso] [durationMinutes] [results]');
		process.exit(2);
	}

	outputJson(await fetchStationBoard({
		station: stationQuery,
		mode: boardMode,
		when: whenIso,
		duration: Number.parseInt(durationArg, 10),
		results: Number.parseInt(resultsArg, 10),
	}));
}
