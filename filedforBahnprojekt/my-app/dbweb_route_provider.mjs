import {createClient} from 'db-vendo-client';
import {profile as dbnavProfile} from 'db-vendo-client/p/dbnav/index.js';
import {profile as dbwebProfile} from 'db-vendo-client/p/dbweb/index.js';
import {readSimplifiedStations} from 'db-hafas-stations';

const formatProviderError = (error) => {
	const status = error?.response?.status;
	const statusText = error?.response?.statusText;
	const url = error?.url || error?.response?.url;
	const message = error?.message || String(error);
	const details = [
		status ? `HTTP ${status}` : null,
		statusText && statusText !== message ? statusText : null,
		message,
		url ? `at ${url}` : null,
	].filter(Boolean);

	return details.join(' ');
};

const exitWithProviderError = (error) => {
	console.error(formatProviderError(error));
	process.exit(1);
};

process.on('uncaughtException', exitWithProviderError);
process.on('unhandledRejection', exitWithProviderError);

const [fromQuery, toQuery, departureIso, includeLongDistanceArg, profileArg = 'dbweb'] = process.argv.slice(2);

if (!fromQuery || !toQuery || !departureIso) {
	console.error('Usage: node dbweb_route_provider.mjs <from> <to> <departureIso> <includeLongDistance> [dbnav|dbweb]');
	process.exit(2);
}

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

const includeLongDistance = includeLongDistanceArg !== 'false';
const defaultDbnavUserAgent = 'OnPoint Bahnprojekt/1.0 (https://bahn.juhermes.de; https://juhermes.de)';
const defaultDbwebUserAgent = 'Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';
const userAgent = profileName === 'dbnav'
	? process.env.DBNAV_USER_AGENT || process.env.DB_ROUTE_USER_AGENT || defaultDbnavUserAgent
	: process.env.DBWEB_USER_AGENT || process.env.DB_ROUTE_USER_AGENT || defaultDbwebUserAgent;
const productgattungen = includeLongDistance
	? ['ICE', 'EC_IC', 'IR', 'REGIONAL', 'SBAHN', 'BUS', 'SCHIFF', 'UBAHN', 'TRAM', 'ANRUFPFLICHTIG']
	: ['REGIONAL', 'SBAHN', 'BUS', 'SCHIFF', 'UBAHN', 'TRAM', 'ANRUFPFLICHTIG'];

const client = createClient(selectedProfile, userAgent);

const repairTextEncoding = (value) => {
	const text = String(value || '');

	if (!/[\u00c2\u00c3]/.test(text)) {
		return text;
	}

	const repaired = Buffer.from(text, 'latin1').toString('utf8');
	return repaired || text;
};

const normalizeStationName = (value) => String(value || '')
	.toLowerCase()
	.normalize('NFD')
	.replace(/[\u0300-\u036f]/g, '')
	.replace(/\u00df/g, 'ss')
	.replace(/[^a-z0-9]+/g, ' ')
	.trim();

const findLocalStation = async (query) => {
	const repairedQuery = repairTextEncoding(query);
	const normalizedQuery = normalizeStationName(repairedQuery);
	let bestStation = null;

	for await (const station of readSimplifiedStations()) {
		const normalizedName = normalizeStationName(station.name);

		if (normalizedName === normalizedQuery) {
			return station;
		}

		if (!bestStation && normalizedName.includes(normalizedQuery)) {
			bestStation = station;
		}
	}

	return bestStation;
};

const formatTrainDisplayName = (vehicle) => {
	const label = vehicle.mittelText || vehicle.kurzText || vehicle.langText || vehicle.name || vehicle.nummer || vehicle.linienNummer;
	const number = vehicle.nummer || vehicle.name;

	if (!label || !number) {
		return label || number || null;
	}

	if (String(label).includes(String(number))) {
		return label;
	}

	if (/\d/.test(String(label))) {
		return `${label} (${number})`;
	}

	return `${label} ${number}`;
};

const findStation = async (query) => {
	const repairedQuery = repairTextEncoding(query);
	const localStation = await findLocalStation(repairedQuery);
	if (localStation) {
		return localStation;
	}

	const locations = await client.locations(repairedQuery, {
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

const from = await findStation(fromQuery);
const to = await findStation(toQuery);

const stationName = (station) => station?.name || 'N/A';

const formatClientTrainDisplayName = (line, fallback) => {
	const label = line?.name || line?.productName || fallback;
	const number = line?.fahrtNr;

	if (!label || !number) {
		return label || number || null;
	}

	if (String(label).includes(String(number))) {
		return label;
	}

	if (/\d/.test(String(label))) {
		return `${label} (${number})`;
	}

	return `${label} ${number}`;
};

const fetchDbnavJourneys = async () => {
	const response = await client.journeys(from.id, to.id, {
		departure: new Date(departureIso),
		results: 10,
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
			bus: true,
			ferry: true,
			subway: true,
			tram: true,
			taxi: true,
		},
	});

	return (response.journeys || [])
		.map((journey) => {
			const legs = [];

			for (const leg of journey.legs || []) {
				if (leg.walking || leg.transfer) {
					continue;
				}

				const trainName = formatClientTrainDisplayName(leg.line, leg.tripId);
				const matchName = leg.line?.fahrtNr || leg.line?.name || trainName;
				const departure = leg.plannedDeparture || leg.departure;
				const arrival = leg.plannedArrival || leg.arrival;

				if (!trainName || !matchName || !departure || !arrival) {
					continue;
				}

				legs.push({
					name: trainName,
					match_name: matchName,
					origin: stationName(leg.origin),
					destination: stationName(leg.destination),
					departure,
					arrival,
				});
			}

			return {legs};
		})
		.filter((journey) => journey.legs.length > 0);
};

if (profileName === 'dbnav') {
	console.log(JSON.stringify({journeys: await fetchDbnavJourneys()}));
	process.exit(0);
}

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
	reisende: [
		{
			typ: 'ERWACHSENER',
			anzahl: 1,
			alter: [],
			ermaessigungen: [{art: 'KEINE_ERMAESSIGUNG', klasse: 'KLASSENLOS'}],
		},
	],
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

if (!response.ok) {
	throw new Error(`DB web routing failed: ${response.status} ${await response.text()}`);
}

const data = await response.json();
const journeys = (data.verbindungen || [])
	.map((connection) => {
		const legs = [];

		for (const section of connection.verbindungsAbschnitte || []) {
			const vehicle = section.verkehrsmittel || {};
			const trainName = formatTrainDisplayName(vehicle);
			const matchName = vehicle.nummer || vehicle.name || vehicle.linienNummer || trainName;
			const departure = section.abfahrt?.sollzeit || section.startHalt?.abfahrt?.sollzeit;
			const arrival = section.ankunft?.sollzeit || section.zielHalt?.ankunft?.sollzeit;

			if (!trainName || !matchName || !departure || !arrival) {
				continue;
			}

			legs.push({
				name: trainName,
				match_name: matchName,
				origin: section.abfahrtsOrt || section.startHalt?.name,
				destination: section.ankunftsOrt || section.zielHalt?.name,
				departure,
				arrival,
			});
		}

		return {legs};
	})
	.filter((journey) => journey.legs.length > 0);

console.log(JSON.stringify({journeys}));
