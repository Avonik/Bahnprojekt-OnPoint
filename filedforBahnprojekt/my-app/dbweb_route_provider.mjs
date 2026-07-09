import {createClient} from 'db-vendo-client';
import {profile as dbwebProfile} from 'db-vendo-client/p/dbweb/index.js';

const [fromQuery, toQuery, departureIso, includeLongDistanceArg] = process.argv.slice(2);

if (!fromQuery || !toQuery || !departureIso) {
	console.error('Usage: node dbweb_route_provider.mjs <from> <to> <departureIso> <includeLongDistance>');
	process.exit(2);
}

const includeLongDistance = includeLongDistanceArg !== 'false';
const productgattungen = includeLongDistance
	? ['ICE', 'EC_IC', 'IR', 'REGIONAL', 'SBAHN', 'BUS', 'SCHIFF', 'UBAHN', 'TRAM', 'ANRUFPFLICHTIG']
	: ['REGIONAL', 'SBAHN', 'BUS', 'SCHIFF', 'UBAHN', 'TRAM', 'ANRUFPFLICHTIG'];

const client = createClient(dbwebProfile, 'BahnProjekt route provider');

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

const from = await findStation(fromQuery);
const to = await findStation(toQuery);

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
		'accept-language': 'en',
		'content-type': 'application/json',
		'user-agent': 'BahnProjekt route provider',
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
