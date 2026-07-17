import {createClient} from 'db-vendo-client';
import {profile as dbnavProfile} from 'db-vendo-client/p/dbnav/index.js';
import {profile as dbwebProfile} from 'db-vendo-client/p/dbweb/index.js';
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

// db-vendo-client logs failed HTTP response bodies through console.log. Keep
// stdout machine-readable even when one request in a batch fails.
const outputJson = (value) => process.stdout.write(`${JSON.stringify(value)}\n`);
console.log = (...values) => console.error(...values);

const args = process.argv.slice(2);
const batchMode = args[0] === '--batch';
const profileArg = batchMode ? args[1] || 'dbweb' : args[4] || 'dbweb';
const profileName = profileArg.toLowerCase();
const selectedProfile = profileName === 'dbnav'
	? dbnavProfile
	: profileName === 'dbweb'
		? dbwebProfile
		: null;

if (!selectedProfile) {
	console.error(`Unknown DB route profile: ${profileArg}`);
	process.exit(2);
}

const defaultDbnavUserAgent = 'OnPoint Bahnprojekt/1.0 (https://bahn.juhermes.de; https://juhermes.de)';
const defaultDbwebUserAgent = 'Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';
const userAgent = profileName === 'dbnav'
	? process.env.DBNAV_USER_AGENT || process.env.DB_ROUTE_USER_AGENT || defaultDbnavUserAgent
	: process.env.DBWEB_USER_AGENT || process.env.DB_ROUTE_USER_AGENT || defaultDbwebUserAgent;
const client = createClient(selectedProfile, userAgent);

const repairTextEncoding = (value) => {
	const text = String(value || '');
	if (!/[\u00c2\u00c3]/.test(text)) return text;
	return Buffer.from(text, 'latin1').toString('utf8') || text;
};

const normalizeStationName = (value) => String(value || '')
	.toLowerCase()
	.normalize('NFD')
	.replace(/[\u0300-\u036f]/g, '')
	.replace(/\u00df/g, 'ss')
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
	const repairedQuery = repairTextEncoding(query);
	const normalizedQuery = normalizeStationName(repairedQuery);
	const {exact, stations} = await loadStationIndex();
	const exactMatch = exact.get(normalizedQuery);
	if (exactMatch) return exactMatch;

	const hbfMatch = exact.get(`${normalizedQuery} hbf`);
	if (hbfMatch) return hbfMatch;

	const partialMatches = stations
		.filter(({normalizedName}) => normalizedName.includes(normalizedQuery))
		.sort((left, right) => left.normalizedName.length - right.normalizedName.length);
	if (partialMatches[0]) return partialMatches[0].station;

	const locations = await client.locations(repairedQuery, {
		results: 1,
		stops: true,
		addresses: false,
		poi: false,
	});
	if (!locations?.[0]) throw new Error(`No station found for ${query}`);
	return locations[0];
};

const findStation = (query) => {
	const key = normalizeStationName(repairTextEncoding(query));
	if (!stationCache.has(key)) stationCache.set(key, resolveStation(query));
	return stationCache.get(key);
};

const stationName = (station) => station?.name || 'N/A';
const stationId = (station) => String(
	station?.id
	|| station?.evaNr
	|| station?.evaNumber
	|| station?.locationId
	|| ''
);

const formatTrainDisplayName = (vehicle) => {
	const label = vehicle.mittelText || vehicle.kurzText || vehicle.langText || vehicle.name || vehicle.nummer || vehicle.linienNummer;
	const number = vehicle.nummer || vehicle.name;
	if (!label || !number) return label || number || null;
	if (String(label).includes(String(number))) return label;
	if (/\d/.test(String(label))) return `${label} (${number})`;
	return `${label} ${number}`;
};

const formatClientTrainDisplayName = (line, fallback) => {
	const label = line?.name || line?.productName || fallback;
	const number = line?.fahrtNr;
	if (!label || !number) return label || number || null;
	if (String(label).includes(String(number))) return label;
	if (/\d/.test(String(label))) return `${label} (${number})`;
	return `${label} ${number}`;
};

const fetchDbnavJourneys = async (from, to, departureIso, includeLongDistance, results) => {
	const response = await client.journeys(from.id, to.id, {
		departure: new Date(departureIso),
		results,
		transfers: 10,
		transferTime: 5,
		stopovers: false,
		language: 'de',
		products: {
			nationalExpress: includeLongDistance,
			national: includeLongDistance,
			regionalExpress: true,
			regional: true,
			suburban: true,
			bus: false,
			ferry: false,
			subway: false,
			tram: false,
			taxi: false,
		},
	});

	return (response.journeys || []).map((journey) => {
		const legs = [];
		for (const leg of journey.legs || []) {
			if (leg.walking || leg.transfer) continue;
			const trainName = formatClientTrainDisplayName(leg.line, leg.tripId);
			// The station-board scraper stores line.name. Prefer the same value
			// here; fahrtNr is often an internal operating number for regional
			// services and therefore does not match the historical train name.
			const matchName = leg.line?.name || trainName || leg.line?.fahrtNr;
			const departure = leg.plannedDeparture || leg.departure;
			const arrival = leg.plannedArrival || leg.arrival;
			if (!trainName || !matchName || !departure || !arrival) continue;
			legs.push({
				name: trainName,
				match_name: matchName,
				origin: stationName(leg.origin),
				origin_id: stationId(leg.origin),
				destination: stationName(leg.destination),
				destination_id: stationId(leg.destination),
				departure,
				arrival,
			});
		}
		return {legs};
	}).filter((journey) => journey.legs.length > 0).slice(0, results);
};

const fetchDbwebJourneys = async (from, to, departureIso, includeLongDistance, results) => {
	const productgattungen = includeLongDistance
		? ['ICE', 'EC_IC', 'IR', 'REGIONAL', 'SBAHN']
		: ['REGIONAL', 'SBAHN'];
	const body = {
		minUmstiegszeit: 0,
		deutschlandTicketVorhanden: false,
		nurDeutschlandTicketVerbindungen: false,
		reservierungsKontingenteVorhanden: false,
		schnelleVerbindungen: true,
		sitzplatzOnly: false,
		abfahrtsHalt: `A=1@L=${from.id}@`,
		ankunftsHalt: `A=1@L=${to.id}@`,
		produktgattungen: productgattungen,
		bikeCarriage: false,
		anfrageZeitpunkt: departureIso.slice(0, 19),
		ankunftSuche: 'ABFAHRT',
		klasse: 'KLASSE_2',
		reisende: [{
			typ: 'ERWACHSENER',
			anzahl: 1,
			alter: [],
			ermaessigungen: [{art: 'KEINE_ERMAESSIGUNG', klasse: 'KLASSENLOS'}],
		}],
	};
	const response = await fetch('https://int.bahn.de/web/api/angebote/fahrplan', {
		method: 'POST',
		headers: {
			accept: 'application/json',
			'accept-language': 'de-DE,de;q=0.9,en;q=0.8',
			'content-type': 'application/json',
			'user-agent': userAgent,
		},
		body: JSON.stringify(body),
	});
	if (!response.ok) throw new Error(`DB web routing failed: ${response.status} ${await response.text()}`);

	const data = await response.json();
	return (data.verbindungen || []).map((connection) => {
		const legs = [];
		for (const section of connection.verbindungsAbschnitte || []) {
			const vehicle = section.verkehrsmittel || {};
			const trainName = formatTrainDisplayName(vehicle);
			const matchName = vehicle.mittelText
				|| vehicle.kurzText
				|| vehicle.langText
				|| vehicle.name
				|| vehicle.linienNummer
				|| trainName
				|| vehicle.nummer;
			const departure = section.abfahrt?.sollzeit || section.startHalt?.abfahrt?.sollzeit;
			const arrival = section.ankunft?.sollzeit || section.zielHalt?.ankunft?.sollzeit;
			if (!trainName || !matchName || !departure || !arrival) continue;
			legs.push({
				name: trainName,
				match_name: matchName,
				origin: section.abfahrtsOrt || section.startHalt?.name,
				origin_id: stationId(section.startHalt || section.abfahrt),
				destination: section.ankunftsOrt || section.zielHalt?.name,
				destination_id: stationId(section.zielHalt || section.ankunft),
				departure,
				arrival,
			});
		}
		return {legs};
	}).filter((journey) => journey.legs.length > 0).slice(0, results);
};

const fetchJourneys = async ({from, to, departure, includeLongDistance = true, results = 10}) => {
	const [fromStation, toStation] = await Promise.all([findStation(from), findStation(to)]);
	return profileName === 'dbnav'
		? fetchDbnavJourneys(fromStation, toStation, departure, includeLongDistance, results)
		: fetchDbwebJourneys(fromStation, toStation, departure, includeLongDistance, results);
};

const mapWithConcurrency = async (items, concurrency, mapper) => {
	const output = new Array(items.length);
	let nextIndex = 0;
	const worker = async () => {
		while (true) {
			const index = nextIndex++;
			if (index >= items.length) return;
			output[index] = await mapper(items[index], index);
		}
	};
	await Promise.all(Array.from({length: Math.min(concurrency, Math.max(1, items.length))}, worker));
	return output;
};

const readStdin = async () => {
	let input = '';
	for await (const chunk of process.stdin) input += chunk;
	return input;
};

if (batchMode) {
	const concurrency = Math.max(1, Number.parseInt(args[2] || '3', 10));
	const payload = JSON.parse(await readStdin());
	const requests = Array.isArray(payload.requests) ? payload.requests : [];
	const responses = await mapWithConcurrency(requests, concurrency, async (request, index) => {
		try {
			return {id: request.id ?? index, journeys: await fetchJourneys(request)};
		} catch (error) {
			return {id: request.id ?? index, error: formatProviderError(error)};
		}
	});
	outputJson({responses});
} else {
	const [from, to, departure, includeLongDistanceArg] = args;
	if (!from || !to || !departure) {
		console.error('Usage: bun dbweb_route_provider.mjs <from> <to> <departureIso> <includeLongDistance> [dbnav|dbweb]');
		process.exit(2);
	}
	const journeys = await fetchJourneys({
		from,
		to,
		departure,
		includeLongDistance: includeLongDistanceArg !== 'false',
		results: 10,
	});
	outputJson({journeys});
}
