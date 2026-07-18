<script lang="ts">
  import { onDestroy, onMount, tick } from 'svelte';
  import { language } from '$lib/i18n';

  const stations = [
    'Altenbeken',
    'Braunschweig Hbf',
    'Bremen Hbf',
    'Celle',
    'Emden Hbf',
    'Göttingen',
    'Hamburg Hbf',
    'Hamburg-Harburg',
    'Hamm(Westf)Hbf',
    'Hameln',
    'Hannover Hbf',
    'Herford',
    'Hildesheim Hbf',
    'Kiel Hbf',
    'Lehrte',
    'Leer(Ostfriesl)',
    'Lingen(Ems)',
    'Löhne(Westf)',
    'Lüneburg',
    'Magdeburg Hbf',
    'Minden(Westf)',
    'Münster(Westf) Hbf',
    'Nienburg(Weser)',
    'Oldenburg(Oldb)',
    'Osnabrück Hbf',
    'Paderborn Hbf',
    'Rheine',
    'Rotenburg(Wümme)',
    'Stendal Hbf',
    'Uelzen',
    'Verden(Aller)',
    'Wolfsburg Hbf'
  ];

  const copy = {
    de: {
      pageTitle: 'OnPoint. | Routenplaner',
      heroTitle: 'OnPoint. findet die Route, die nicht nur schnell aussieht.',
      heroIntro:
        'Vergleiche Bahnverbindungen nach Dauer, Umstiegen und historischen Anschlussrisiken.',
      route: 'Route',
      searchConnection: 'Verbindung suchen',
      start: 'Start',
      startStation: 'Startbahnhof',
      destination: 'Ziel',
      destinationStation: 'Zielbahnhof',
      swapStations: 'Start und Ziel tauschen',
      earliestDeparture: 'Früheste Abfahrt',
      regionalOnly: 'Nur Regionalverkehr',
      regionalHelp: 'Erklärung: Nur Regionalverkehr',
      regionalTooltip:
        'Schließt ICE, IC und EC aus und sucht nur Verbindungen mit Regionalverkehr, S-Bahn und ähnlichen Nahverkehrsangeboten.',
      analysisRunning: 'Analyse läuft',
      findBestRoute: 'Beste Route finden',
      loadingMessages: [
        'Live-Verbindungen werden abgefragt',
        'Historische Verspätungen werden verglichen',
        'Anschlüsse werden simuliert',
        'Plan-B-Routen werden gesucht',
        'Empfehlung wird sortiert'
      ],
      analysis: 'Analyse',
      foundOptions: 'Gefundene Optionen',
      options: 'Optionen',
      trackedTrains: 'getrackte Züge',
      recommendation: 'Empfehlung',
      option: 'Option',
      success: 'Erfolg',
      duration: 'Dauer',
      expected: 'Erwartet',
      transfers: 'Umstiege',
      riskTime: 'Risikozeit',
      firstTrain: 'Startzug',
      with: 'mit',
      connectionChance: 'Anschlusschance',
      plannedExpectedArrival: 'Ankunft geplant / erwartet',
      plannedExpectedDeparture: 'Weiterfahrt geplant / erwartet',
      dataPoints: 'Datenpunkte',
      historicalMatches: 'historische Treffer',
      riskCost: 'Risikokosten',
      failure: 'Fehlschlag',
      planBLoss: 'Plan-B-Verlust',
      planB: 'Plan B bei verpasstem Anschluss',
      searchFrom: 'Suche ab',
      comparedWithOriginal: 'gegenüber der ursprünglichen Verbindung',
      noReliableAlternative: 'Keine verlässliche Alternative gefunden',
      fallbackDefaultBefore: 'Für die Bewertung wird eine mögliche Zusatzverspätung von',
      fallbackDefaultAfter: 'angenommen.',
      directConnection: 'Direktverbindung ohne Umstieg',
      arrival: 'Ankunft',
      minutesTransfer: 'min Umstieg',
      statusRisk: 'riskant',
      statusTight: 'knapp',
      statusStable: 'stabil',
      faqTitle: 'Häufige Fragen',
      faq: [
        {
          question: 'Wie entsteht die Empfehlung?',
          answer:
            'OnPoint. kombiniert aktuelle Verbindungen mit historischen Verspätungen der beteiligten Züge und Bahnhöfe. Bewertet werden Fahrzeit, Umstiege, Anschlusschancen und die Folgen eines verpassten Anschlusses.'
        },
        {
          question: 'Was bedeutet die Anschlusschance?',
          answer:
            'Sie ist eine Schätzung dafür, wie wahrscheinlich ein Umstieg unter ähnlichen Bedingungen klappt. Sie hilft beim Vergleichen, ist aber keine Garantie für eine einzelne Reise.'
        },
        {
          question: 'Welche historischen Daten werden verwendet?',
          answer:
            'Verwendet werden gespeicherte Ankunfts- und Abfahrtsverspätungen sowie bekannte Ausfälle an den unterstützten Bahnhöfen. Persönliche Reisedaten werden dafür nicht benötigt.'
        },
        {
          question: 'Werden Zugausfälle berücksichtigt?',
          answer:
            'Bekannte Ausfälle fließen in die historischen Auswertungen ein. Kurzfristige Änderungen können trotzdem erst sichtbar werden, wenn sie in den aktuellen Fahrplandaten auftauchen.'
        },
        {
          question: 'Warum wird nicht immer die schnellste Route empfohlen?',
          answer:
            'Ein sehr kurzer Umstieg kann auf dem Papier schnell sein, aber ein hohes Risiko und einen großen Zeitverlust verursachen. Deshalb kann eine etwas längere, robustere Route besser abschneiden.'
        },
        {
          question: 'Was bedeuten Risikozeit und Plan B?',
          answer:
            'Die Risikozeit schätzt den erwartbaren Zeitverlust durch mögliche Anschlussprobleme. Der Plan B zeigt eine Alternative, die nach einem verpassten Anschluss voraussichtlich verfügbar wäre.'
        },
        {
          question: 'Sind die Ergebnisse eine Garantie oder ein Ticketangebot?',
          answer:
            'Nein. Die Werte sind datenbasierte Schätzungen und ersetzen keine Live-Anzeige des Verkehrsunternehmens. Tickets, Preise und verbindliche Reiseinformationen erhalten Sie beim jeweiligen Anbieter.'
        }
      ],
      footerProject: 'Ein Bahnprojekt von Julian Hermes.',
      footerAria: 'Links im Seitenfuß',
      copyright:
        '© 2026 Julian Hermes. Datenquellen: importierte historische Bahn-Dumps, Deutsche Bahn Web API, db-vendo-client/pyhafas.',
      errors: {
        missingFields: 'Bitte wählen Sie Start, Ziel und Abfahrtszeit aus.',
        sameStation: 'Start und Ziel müssen unterschiedlich sein.',
        noConnection:
          'Für diese Auswahl wurde keine passende Verbindung gefunden. Versuchen Sie eine andere Uhrzeit oder Route.',
        busy: 'Gerade suchen viele Personen gleichzeitig. Bitte versuchen Sie es gleich noch einmal.',
        timeout: 'Die Suche dauert ungewöhnlich lange. Bitte versuchen Sie es noch einmal.',
        unavailable:
          'Die Verbindungssuche ist momentan nicht erreichbar. Bitte versuchen Sie es später erneut.',
        requestFailed: 'Die Verbindung konnte nicht geladen werden. Bitte versuchen Sie es erneut.'
      }
    },
    en: {
      pageTitle: 'OnPoint. | Journey planner',
      heroTitle: 'OnPoint. finds the route that does more than look fast.',
      heroIntro:
        'Compare train journeys by duration, transfers and historical connection risks.',
      route: 'Route',
      searchConnection: 'Find a connection',
      start: 'From',
      startStation: 'Departure station',
      destination: 'To',
      destinationStation: 'Destination station',
      swapStations: 'Swap departure and destination',
      earliestDeparture: 'Earliest departure',
      regionalOnly: 'Regional trains only',
      regionalHelp: 'About regional trains only',
      regionalTooltip:
        'Excludes ICE, IC and EC services and searches only for regional trains, suburban trains and similar local services.',
      analysisRunning: 'Analysing',
      findBestRoute: 'Find the best route',
      loadingMessages: [
        'Checking live connections',
        'Comparing historical delays',
        'Simulating transfers',
        'Looking for backup routes',
        'Ranking recommendations'
      ],
      analysis: 'Analysis',
      foundOptions: 'Journey options',
      options: 'Options',
      trackedTrains: 'tracked trains',
      recommendation: 'Recommended',
      option: 'Option',
      success: 'Success',
      duration: 'Duration',
      expected: 'Expected',
      transfers: 'Transfers',
      riskTime: 'Risk time',
      firstTrain: 'First train',
      with: 'on',
      connectionChance: 'connection chance',
      plannedExpectedArrival: 'Scheduled / expected arrival',
      plannedExpectedDeparture: 'Scheduled / expected departure',
      dataPoints: 'Data points',
      historicalMatches: 'historical matches',
      riskCost: 'Risk cost',
      failure: 'failure',
      planBLoss: 'backup delay',
      planB: 'Backup if the connection is missed',
      searchFrom: 'Search from',
      comparedWithOriginal: 'compared with the original journey',
      noReliableAlternative: 'No reliable alternative found',
      fallbackDefaultBefore: 'For the score, a possible additional delay of',
      fallbackDefaultAfter: 'is assumed.',
      directConnection: 'Direct connection with no transfer',
      arrival: 'Arrival',
      minutesTransfer: 'min transfer',
      statusRisk: 'at risk',
      statusTight: 'tight',
      statusStable: 'stable',
      faqTitle: 'Frequently asked questions',
      faq: [
        {
          question: 'How is the recommendation calculated?',
          answer:
            'OnPoint. combines current connections with historical delays for the trains and stations involved. It considers travel time, transfers, connection chances and the impact of a missed connection.'
        },
        {
          question: 'What does connection chance mean?',
          answer:
            'It estimates how likely a transfer is to work under similar conditions. It is useful for comparing journeys, but it cannot guarantee the outcome of an individual trip.'
        },
        {
          question: 'Which historical data is used?',
          answer:
            'The analysis uses stored arrival and departure delays as well as known cancellations at supported stations. No personal travel data is required.'
        },
        {
          question: 'Are train cancellations included?',
          answer:
            'Known cancellations are included in the historical analysis. Last-minute changes may still appear only after they become available in current timetable data.'
        },
        {
          question: 'Why is the fastest route not always recommended?',
          answer:
            'A very short transfer may look fast but carry a high risk and a large delay if missed. A slightly longer and more robust journey can therefore rank higher.'
        },
        {
          question: 'What are risk time and the backup route?',
          answer:
            'Risk time estimates the expected time lost through possible connection problems. The backup shows an alternative that would likely be available after a missed connection.'
        },
        {
          question: 'Are the results a guarantee or a ticket offer?',
          answer:
            'No. The values are data-based estimates and do not replace the operator’s live information. Tickets, prices and binding travel information remain with the relevant provider.'
        }
      ],
      footerProject: 'A railway project by Julian Hermes.',
      footerAria: 'Footer links',
      copyright:
        '© 2026 Julian Hermes. Data sources: imported historical railway data, Deutsche Bahn Web API, db-vendo-client/pyhafas.',
      errors: {
        missingFields: 'Please select a departure, destination and departure time.',
        sameStation: 'Departure and destination must be different.',
        noConnection:
          'No suitable connection was found. Try a different time or another route.',
        busy: 'A lot of people are searching right now. Please try again in a moment.',
        timeout: 'The search is taking unusually long. Please try again.',
        unavailable: 'Journey search is currently unavailable. Please try again later.',
        requestFailed: 'The connection could not be loaded. Please try again.'
      }
    }
  } as const;

  type ErrorKey = keyof typeof copy.de.errors;

  let startingLocation = '';
  let endLocation = '';
  let time = '';
  let data: any;
  let onlyRegionalverkehr = false;
  let loading = false;
  let loadingMessageIndex = 0;
  let loadingTimer: ReturnType<typeof setInterval> | undefined;
  let errorKey: ErrorKey | '' = '';
  let journeyDetailsRef: HTMLElement;

  $: t = copy[$language];

  onMount(() => {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset() + 30);
    time = now.toISOString().slice(0, 16);
  });

  onDestroy(() => {
    stopLoadingAnimation();
  });

  function startLoadingAnimation() {
    stopLoadingAnimation();
    loadingMessageIndex = 0;
    loadingTimer = setInterval(() => {
      loadingMessageIndex = (loadingMessageIndex + 1) % t.loadingMessages.length;
    }, 5200);
  }

  function stopLoadingAnimation() {
    if (loadingTimer) {
      clearInterval(loadingTimer);
      loadingTimer = undefined;
    }
  }

  function swapStations() {
    [startingLocation, endLocation] = [endLocation, startingLocation];
  }

  function confidenceTone(value: number) {
    if (value >= 90) return 'confidence-good';
    if (value >= 70) return 'confidence-ok';
    return 'confidence-risk';
  }

  function minutesBetween(start: string, end: string) {
    const [startHour, startMinute] = start.split(':').map(Number);
    const [endHour, endMinute] = end.split(':').map(Number);
    let minutes = endHour * 60 + endMinute - (startHour * 60 + startMinute);
    if (minutes < 0) minutes += 24 * 60;
    return minutes;
  }

  function transferLabel(leg: any) {
    const plannedLayover = Number(leg.planned_layover_minutes);
    if (Number.isFinite(plannedLayover)) {
      return `${Math.round(plannedLayover)} ${t.minutesTransfer}`;
    }

    const planned = minutesBetween(leg.planned_arrival, leg.planned_departure);
    return `${planned} ${t.minutesTransfer}`;
  }

  function connectionProbability(leg: any) {
    return Number(leg.connection_success_probability ?? (leg.layover_feasible ? 100 : 0));
  }

  function connectionStatus(leg: any) {
    const probability = connectionProbability(leg);

    if (!leg.layover_feasible || probability < 60) {
      return { label: t.statusRisk, className: 'status-risk' };
    }
    if (probability < 85) return { label: t.statusTight, className: 'status-ok' };
    return { label: t.statusStable, className: 'status-good' };
  }

  function minutesLabel(value: unknown) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return '0 min';
    return `${Math.round(numericValue)} min`;
  }

  function signedMinutesLabel(value: unknown) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return '+0 min';
    return `+${Math.round(numericValue)} min`;
  }

  async function sendData() {
    loading = true;
    startLoadingAnimation();
    errorKey = '';
    data = undefined;

    if (!startingLocation || !endLocation || !time) {
      errorKey = 'missingFields';
      loading = false;
      stopLoadingAnimation();
      return;
    }

    if (startingLocation === endLocation) {
      errorKey = 'sameStation';
      loading = false;
      stopLoadingAnimation();
      return;
    }

    const controller = new AbortController();
    const requestTimeout = window.setTimeout(() => controller.abort(), 90000);

    try {
      const response = await fetch('/api/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          starting_location: startingLocation,
          end_location: endLocation,
          time,
          only_regionalverkehr: onlyRegionalverkehr
        }),
        signal: controller.signal
      });

      if (!response.ok) {
        errorKey =
          response.status === 429
            ? 'busy'
            : response.status >= 500
              ? 'unavailable'
              : 'requestFailed';
        return;
      }

      const payload = await response.json().catch(() => undefined);
      data = payload;

      if (data?.journeys?.journeys?.length) {
        data.journeys.journeys.sort((a: any, b: any) =>
          Number(Boolean(b.best_journey)) - Number(Boolean(a.best_journey))
        );
      } else {
        errorKey = 'noConnection';
      }
    } catch (error) {
      errorKey =
        error instanceof DOMException && error.name === 'AbortError' ? 'timeout' : 'unavailable';
    } finally {
      window.clearTimeout(requestTimeout);
      loading = false;
      stopLoadingAnimation();
    }

    if (data?.journeys?.journeys?.length) {
      await tick();
      journeyDetailsRef.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }
</script>

<svelte:head>
  <title>{t.pageTitle}</title>
</svelte:head>

<main class="planner-shell">
  <section id="plan" class="planner-hero">
    <div class="hero-copy">
      <h1>{t.heroTitle}</h1>
      <p class="intro">{t.heroIntro}</p>
    </div>

    <form class="planner-panel" onsubmit={(event) => { event.preventDefault(); sendData(); }}>
      <div class="panel-heading">
        <div>
          <p class="eyebrow">{t.route}</p>
          <h2>{t.searchConnection}</h2>
        </div>
      </div>

      <div class="route-grid">
        <label class="field">
          <span>{t.start}</span>
          <select bind:value={startingLocation} aria-label={t.startStation}>
            <option value="" disabled>{t.startStation}</option>
            {#each stations as station}
              <option value={station}>{station}</option>
            {/each}
          </select>
        </label>

        <button class="swap-button" type="button" onclick={swapStations} aria-label={t.swapStations}>
          ⇄
        </button>

        <label class="field">
          <span>{t.destination}</span>
          <select bind:value={endLocation} aria-label={t.destinationStation}>
            <option value="" disabled>{t.destinationStation}</option>
            {#each stations as station}
              <option value={station}>{station}</option>
            {/each}
          </select>
        </label>
      </div>

      <label class="field departure-field">
        <span>{t.earliestDeparture}</span>
        <input type="datetime-local" bind:value={time} />
      </label>

      <label class="regional-toggle">
        <input type="checkbox" bind:checked={onlyRegionalverkehr} />
        <span>{t.regionalOnly}</span>
        <button class="help-bubble" type="button" aria-label={t.regionalHelp}>
          ?
          <span class="tooltip">{t.regionalTooltip}</span>
        </button>
      </label>

      {#if errorKey}
        <div class="error-banner" role="alert">{t.errors[errorKey]}</div>
      {/if}

      <button class="primary-action" type="submit" disabled={loading}>
        {#if loading}
          <span class="loader"></span>
          {t.analysisRunning}
        {:else}
          {t.findBestRoute}
        {/if}
      </button>

      {#if loading}
        <div class="loading-journey" aria-live="polite">
          <div class="track-loader">
            <span class="track-line"></span>
            <span class="train-loader">
              <span></span>
              <span></span>
              <span></span>
              <span></span>
            </span>
          </div>
          {#key loadingMessageIndex}
            <p>{t.loadingMessages[loadingMessageIndex]}</p>
          {/key}
        </div>
      {/if}
    </form>
  </section>

  {#if data?.journeys?.journeys?.length}
    <section id="results" class="results-section" bind:this={journeyDetailsRef}>
      <div class="section-heading">
        <div>
          <p class="eyebrow">{t.analysis}</p>
          <h2>{t.foundOptions}</h2>
        </div>
        <div class="summary-strip">
          <div>
            <span>{data.journeys.journeys.length}</span>
            <small>{t.options}</small>
          </div>
          <div>
            <span>{data.journeys.sum_tracked_trains ?? 0}</span>
            <small>{t.trackedTrains}</small>
          </div>
        </div>
      </div>

      <div class="route-list">
        {#each data.journeys.journeys as journey, index}
          <details class:recommended={journey.best_journey} class="route-option">
            <summary>
              <div class="option-main">
                <div class="option-title">
                  {#if journey.best_journey}
                    <span class="recommendation">{t.recommendation}</span>
                  {/if}
                  <strong>{t.option} {index + 1}</strong>
                  <span>{journey.start_time} - {journey.end_time}</span>
                </div>

                <div class="route-preview">
                  <span>{startingLocation}</span>
                  <span class="preview-line"></span>
                  <span>{endLocation}</span>
                </div>
              </div>

              <div class="option-metrics">
                <div>
                  <small>{t.success}</small>
                  <strong class={confidenceTone(journey.odds_of_successful_journey)}>{journey.odds_of_successful_journey} %</strong>
                </div>
                <div>
                  <small>{t.duration}</small>
                  <strong>{journey.duration}</strong>
                </div>
                <div>
                  <small>{t.expected}</small>
                  <strong>{minutesLabel(journey.expected_total_cost_minutes)}</strong>
                </div>
                <div>
                  <small>{t.transfers}</small>
                  <strong>{journey.legs.length}</strong>
                </div>
                <div>
                  <small>{t.riskTime}</small>
                  <strong>{signedMinutesLabel(journey.risk_cost_minutes)}</strong>
                </div>
                <div>
                  <small>{t.firstTrain}</small>
                  <strong>{journey.start_train}</strong>
                </div>
                <span class="open-indicator">+</span>
              </div>
            </summary>

            <div class="timeline">
              <div class="timeline-stop start">
                <span class="node"></span>
                <div>
                  <small>{t.start}</small>
                  <strong>{startingLocation}</strong>
                  <p>{journey.start_time} {t.with} {journey.start_train}</p>
                </div>
              </div>

              {#if journey.legs.length}
                {#each journey.legs as leg}
                  {@const status = connectionStatus(leg)}
                  <div class="timeline-transfer" class:risk={status.className === 'status-risk'}>
                    <span class="node"></span>
                    <div class="transfer-card">
                      <div class="transfer-card-head">
                        <div>
                          <small
                            >{transferLabel(leg)} · {connectionProbability(leg)} %
                            {t.connectionChance}</small
                          >
                          <strong>{leg.layover_at}</strong>
                        </div>
                        <span class={status.className}>{status.label}</span>
                      </div>
                      <div class="transfer-grid">
                        <div>
                          <small>{t.plannedExpectedArrival}</small>
                          <strong>{leg.planned_arrival} / {leg.expected_arrival}</strong>
                          <span>{leg.last_train}</span>
                        </div>
                        <div>
                          <small>{t.plannedExpectedDeparture}</small>
                          <strong>{leg.planned_departure} / {leg.expected_departure}</strong>
                          <span>{leg.next_train}</span>
                        </div>
                        <div>
                          <small>{t.dataPoints}</small>
                          <strong>{Number(leg.last_train_tracked ?? 0) + Number(leg.next_train_tracked ?? 0)}</strong>
                          <span>{t.historicalMatches}</span>
                        </div>
                      </div>
                      <div class="risk-details">
                        <div>
                          <small>{t.riskCost}</small>
                          <strong>{signedMinutesLabel(leg.connection_risk_cost_minutes)}</strong>
                          <span
                            >{leg.connection_failure_probability} % {t.failure} ×
                            {minutesLabel(leg.fallback_delay_minutes)} {t.planBLoss}</span
                          >
                        </div>
                        {#if leg.fallback_route}
                          <div>
                            <small>{t.planB}</small>
                            <strong
                              >{leg.fallback_route.departure_time} -
                              {leg.fallback_route.arrival_time} {t.with}
                              {leg.fallback_route.start_train}</strong
                            >
                            <span
                              >{t.searchFrom} {leg.fallback_search_time},
                              {leg.fallback_route.from} → {leg.fallback_route.to},
                              {leg.fallback_route.transfers} {t.transfers.toLowerCase()},
                              {signedMinutesLabel(leg.fallback_route.extra_minutes)}
                              {t.comparedWithOriginal}</span
                            >
                          </div>
                        {:else}
                          <div>
                            <small>{t.planB}</small>
                            <strong>{t.noReliableAlternative}</strong>
                            <span
                              >{t.searchFrom} {leg.fallback_search_time}.
                              {t.fallbackDefaultBefore}
                              {minutesLabel(leg.fallback_delay_minutes)}
                              {t.fallbackDefaultAfter}</span
                            >
                          </div>
                        {/if}
                      </div>
                    </div>
                  </div>
                {/each}
              {:else}
                <div class="timeline-transfer">
                  <span class="node"></span>
                  <div class="transfer-card">
                    <strong>{t.directConnection}</strong>
                  </div>
                </div>
              {/if}

              <div class="timeline-stop end">
                <span class="node"></span>
                <div>
                  <small>{t.destination}</small>
                  <strong>{endLocation}</strong>
                  <p>{t.arrival} {journey.end_time}</p>
                </div>
              </div>
            </div>
          </details>
        {/each}
      </div>
    </section>
  {/if}

  <section id="faq" class="faq-section">
    <div class="section-heading">
      <div>
        <p class="eyebrow">FAQ</p>
        <h2>{t.faqTitle}</h2>
      </div>
    </div>

    <div class="faq-list">
      {#each t.faq as item}
        <details>
          <summary>{item.question}<span>+</span></summary>
          <p>{item.answer}</p>
        </details>
      {/each}
    </div>
  </section>

  <footer id="sources" class="site-footer">
    <div class="footer-inner">
      <div class="footer-brand">
        <img src="/onpoint-logo.svg" alt="" />
        <div>
          <strong>OnPoint.</strong>
          <p>{t.footerProject}</p>
        </div>
      </div>
      <nav class="footer-links" aria-label={t.footerAria}>
        <a class="primary-link" href="https://juhermes.de" target="_blank" rel="noreferrer">juhermes.de</a>
        <a class="primary-link" href="https://github.com/Avonik" target="_blank" rel="noreferrer">GitHub</a>
        <a href="https://www.bahn.de/" target="_blank" rel="noreferrer">Deutsche Bahn</a>
        <a href="https://github.com/public-transport/db-vendo-client" target="_blank" rel="noreferrer">db-vendo-client</a>
        <a href="https://github.com/FahrplanDatenGarten/pyhafas" target="_blank" rel="noreferrer">pyhafas</a>
      </nav>
      <p class="copyright">{t.copyright}</p>
    </div>
  </footer>
</main>

<style>
  :global(html) {
    scroll-behavior: smooth;
  }

  .planner-shell {
    min-height: 100vh;
    color: #edf2f7;
    background:
      linear-gradient(120deg, rgba(15, 23, 42, 0.9), rgba(17, 24, 39, 0.74)),
      url('https://upload.wikimedia.org/wikipedia/commons/a/a8/ICE_3_Oberhaider-Wald-Tunnel.jpg');
    background-attachment: fixed;
    background-position: center;
    background-size: cover;
  }

  .planner-hero,
  .results-section,
  .faq-section {
    width: min(1120px, calc(100% - 32px));
    margin: 0 auto;
  }

  .planner-hero {
    min-height: calc(100vh - 76px);
    display: grid;
    grid-template-columns: minmax(0, 0.9fr) minmax(360px, 1fr);
    align-items: center;
    gap: 40px;
    padding: 56px 0 48px;
  }

  .hero-copy h1 {
    max-width: 780px;
    margin: 0;
    font-size: clamp(2.4rem, 6vw, 5.25rem);
    line-height: 1;
    letter-spacing: 0;
  }

  .intro {
    max-width: 620px;
    margin-top: 22px;
    color: #cbd5e1;
    font-size: 1.08rem;
    line-height: 1.65;
  }

  .eyebrow {
    margin: 0 0 10px;
    color: #67e8f9;
    font-size: 0.78rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .planner-panel,
  .route-option,
  .faq-list details {
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 8px;
    background: rgba(15, 23, 42, 0.9);
    box-shadow: 0 24px 70px rgba(0, 0, 0, 0.3);
    backdrop-filter: blur(18px);
  }

  .planner-panel {
    padding: 28px;
  }

  .panel-heading,
  .section-heading,
  .transfer-card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
  }

  .panel-heading h2,
  .section-heading h2 {
    margin: 0;
    font-size: clamp(1.7rem, 3vw, 2.4rem);
    letter-spacing: 0;
  }

  .route-grid {
    display: grid;
    grid-template-columns: 1fr 42px 1fr;
    align-items: end;
    gap: 12px;
    margin-top: 24px;
  }

  .field {
    display: grid;
    gap: 8px;
  }

  .departure-field {
    margin-top: 30px;
  }

  .field span {
    color: #dbeafe;
    font-size: 0.86rem;
    font-weight: 800;
  }

  select,
  input[type='datetime-local'] {
    min-height: 48px;
    width: 100%;
    border: 1px solid rgba(148, 163, 184, 0.32);
    border-radius: 8px;
    background: rgba(2, 6, 23, 0.62);
    color: #f8fafc;
    padding: 0 14px;
    font: inherit;
  }

  select:focus,
  input:focus,
  button:focus-visible,
  summary:focus-visible,
  .help-bubble:focus-visible {
    outline: 3px solid rgba(103, 232, 249, 0.42);
    outline-offset: 2px;
  }

  select option {
    background: #0f172a;
    color: #f8fafc;
  }

  .swap-button {
    min-width: 42px;
    height: 48px;
    border: 1px solid rgba(103, 232, 249, 0.28);
    border-radius: 8px;
    background: rgba(8, 47, 73, 0.54);
    color: #67e8f9;
    font-size: 1.4rem;
    cursor: pointer;
  }

  .regional-toggle {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 10px;
    margin-top: 16px;
    color: #cbd5e1;
    font-size: 0.92rem;
    white-space: nowrap;
  }

  .regional-toggle input {
    width: 18px;
    height: 18px;
    accent-color: #fbbf24;
  }

  .help-bubble {
    position: relative;
    display: inline-grid;
    place-items: center;
    width: 22px;
    height: 22px;
    border: 1px solid rgba(103, 232, 249, 0.42);
    border-radius: 999px;
    color: #67e8f9;
    font-size: 0.78rem;
    font-weight: 900;
    cursor: help;
  }

  .tooltip {
    position: absolute;
    right: 0;
    bottom: calc(100% + 10px);
    z-index: 20;
    width: min(300px, 80vw);
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 8px;
    background: #020617;
    color: #dbeafe;
    padding: 10px 12px;
    font-size: 0.8rem;
    font-weight: 600;
    line-height: 1.45;
    white-space: normal;
    opacity: 0;
    pointer-events: none;
    transform: translateY(4px);
    transition: opacity 140ms ease, transform 140ms ease;
  }

  .help-bubble:hover .tooltip,
  .help-bubble:focus .tooltip {
    opacity: 1;
    transform: translateY(0);
  }

  .primary-action {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 50px;
    width: 100%;
    margin-top: 22px;
    border: 0;
    border-radius: 8px;
    background: #fbbf24;
    color: #1f2937;
    font-weight: 900;
    cursor: pointer;
  }

  .primary-action:disabled {
    cursor: wait;
    opacity: 0.7;
  }

  .loading-journey {
    margin-top: 16px;
    border: 1px solid rgba(103, 232, 249, 0.2);
    border-radius: 8px;
    background: rgba(8, 47, 73, 0.28);
    padding: 14px;
  }

  .track-loader {
    position: relative;
    height: 34px;
    overflow: hidden;
  }

  .track-line {
    position: absolute;
    left: 0;
    right: 0;
    top: 18px;
    height: 2px;
    background:
      repeating-linear-gradient(
        90deg,
        rgba(148, 163, 184, 0.8) 0,
        rgba(148, 163, 184, 0.8) 10px,
        transparent 10px,
        transparent 18px
      );
  }

  .train-loader {
    position: absolute;
    top: 4px;
    left: -142px;
    display: grid;
    grid-template-columns: 34px 26px 26px 26px;
    gap: 4px;
    width: 128px;
    animation: train-pass 5.4s linear infinite;
  }

  .train-loader span {
    position: relative;
    height: 22px;
    border-radius: 6px 6px 4px 4px;
    background: #fbbf24;
    box-shadow: 0 8px 18px rgba(251, 191, 36, 0.24);
  }

  .train-loader span:first-child {
    border-radius: 14px 6px 4px 4px;
  }

  .train-loader span:last-child {
    border-radius: 6px 14px 4px 4px;
  }

  .train-loader span::after {
    content: '';
    position: absolute;
    top: 5px;
    left: 7px;
    width: 7px;
    height: 6px;
    border-radius: 2px;
    background: rgba(15, 23, 42, 0.75);
    box-shadow: 11px 0 0 rgba(15, 23, 42, 0.75);
  }

  .loading-journey p {
    min-height: 22px;
    margin: 8px 0 0;
    color: #dbeafe;
    font-size: 0.9rem;
    font-weight: 800;
    animation: loading-text 5.2s ease both;
  }

  .error-banner {
    margin-top: 18px;
    border: 1px solid rgba(248, 113, 113, 0.36);
    border-radius: 8px;
    background: rgba(127, 29, 29, 0.32);
    color: #fecaca;
    padding: 12px 14px;
  }

  .results-section,
  .faq-section {
    padding: 40px 0 72px;
  }

  .summary-strip {
    display: grid;
    grid-template-columns: repeat(2, minmax(120px, 1fr));
    gap: 10px;
  }

  .summary-strip div {
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 8px;
    background: rgba(15, 23, 42, 0.7);
    padding: 12px 16px;
  }

  .summary-strip span {
    display: block;
    font-size: 1.5rem;
    font-weight: 900;
  }

  .summary-strip small,
  .option-metrics small,
  .timeline small,
  .transfer-grid small {
    color: #94a3b8;
  }

  .route-list {
    display: grid;
    gap: 14px;
    margin-top: 24px;
  }

  .route-option {
    overflow: hidden;
  }

  .route-option.recommended {
    border-color: rgba(251, 191, 36, 0.8);
    box-shadow: 0 0 0 2px rgba(251, 191, 36, 0.18), 0 24px 70px rgba(0, 0, 0, 0.28);
  }

  .route-option summary {
    display: grid;
    grid-template-columns: minmax(0, 1.1fr) minmax(440px, 0.9fr);
    gap: 18px;
    align-items: center;
    cursor: pointer;
    list-style: none;
    padding: 20px 22px;
  }

  summary::-webkit-details-marker {
    display: none;
  }

  .option-title {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
  }

  .option-title strong {
    font-size: 1.05rem;
  }

  .option-title span:last-child {
    color: #cbd5e1;
    font-weight: 800;
  }

  .recommendation {
    border-radius: 999px;
    background: rgba(251, 191, 36, 0.16);
    color: #fde68a;
    padding: 5px 9px;
    font-size: 0.72rem;
    font-weight: 900;
    text-transform: uppercase;
  }

  .route-preview {
    display: grid;
    grid-template-columns: auto minmax(40px, 1fr) auto;
    align-items: center;
    gap: 10px;
    margin-top: 12px;
    color: #94a3b8;
    font-size: 0.9rem;
    font-weight: 800;
  }

  .preview-line {
    height: 1px;
    min-width: 40px;
    border-top: 1px dashed rgba(148, 163, 184, 0.5);
  }

  .option-metrics {
    display: grid;
    grid-template-columns: 0.9fr 1fr 1fr 0.8fr 0.9fr 1fr 28px;
    align-items: center;
    gap: 12px;
  }

  .option-metrics strong {
    display: block;
    margin-top: 3px;
    overflow-wrap: anywhere;
  }

  .option-metrics strong[class^='confidence'] {
    display: inline-flex;
    border-radius: 999px;
    padding: 5px 9px;
    font-size: 0.86rem;
  }

  .confidence-good {
    background: rgba(34, 197, 94, 0.14);
    color: #86efac;
  }

  .confidence-ok {
    background: rgba(251, 191, 36, 0.16);
    color: #fde68a;
  }

  .confidence-risk {
    background: rgba(248, 113, 113, 0.16);
    color: #fecaca;
  }

  .open-indicator {
    display: grid;
    place-items: center;
    width: 28px;
    height: 28px;
    border-radius: 999px;
    background: rgba(103, 232, 249, 0.1);
    color: #67e8f9;
    font-weight: 900;
    transition: transform 160ms ease;
  }

  details[open] .open-indicator,
  details[open] summary > span {
    transform: rotate(45deg);
  }

  .timeline {
    position: relative;
    display: grid;
    gap: 0;
    padding: 0 22px 24px 40px;
  }

  .timeline-stop,
  .timeline-transfer {
    position: relative;
    display: grid;
    grid-template-columns: 22px minmax(0, 1fr);
    gap: 14px;
    align-items: start;
    padding-bottom: 18px;
  }

  .timeline-stop::after,
  .timeline-transfer::after {
    content: '';
    position: absolute;
    top: 24px;
    bottom: -2px;
    left: 7px;
    border-left: 2px dashed rgba(103, 232, 249, 0.42);
  }

  .timeline > :last-child {
    padding-bottom: 0;
  }

  .timeline > :last-child::after {
    display: none;
  }

  .node {
    position: relative;
    z-index: 1;
    width: 16px;
    height: 16px;
    margin-top: 5px;
    border: 3px solid #67e8f9;
    border-radius: 999px;
    background: #0f172a;
  }

  .timeline-stop.start .node,
  .timeline-stop.end .node {
    border-color: #fbbf24;
  }

  .timeline strong {
    display: block;
    font-size: 1rem;
  }

  .timeline p {
    margin: 4px 0 0;
    color: #cbd5e1;
  }

  .transfer-card {
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 8px;
    background: rgba(2, 6, 23, 0.34);
    padding: 14px;
  }

  .transfer-card-head strong {
    margin-top: 3px;
  }

  .transfer-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin-top: 14px;
  }

  .transfer-grid div {
    border-top: 1px solid rgba(148, 163, 184, 0.16);
    padding-top: 10px;
  }

  .transfer-grid span {
    display: block;
    margin-top: 3px;
    color: #94a3b8;
    overflow-wrap: anywhere;
  }

  .risk-details {
    display: grid;
    grid-template-columns: minmax(180px, 0.75fr) minmax(0, 1.25fr);
    gap: 12px;
    margin-top: 12px;
  }

  .risk-details div {
    border: 1px solid rgba(103, 232, 249, 0.14);
    border-radius: 8px;
    background: rgba(8, 47, 73, 0.22);
    padding: 12px;
  }

  .risk-details strong,
  .risk-details span {
    display: block;
  }

  .risk-details strong {
    margin-top: 4px;
  }

  .risk-details span {
    margin-top: 5px;
    color: #94a3b8;
    line-height: 1.45;
  }

  .status-good,
  .status-ok,
  .status-risk {
    border-radius: 999px;
    padding: 4px 8px;
    font-size: 0.72rem;
    font-weight: 900;
    text-transform: uppercase;
  }

  .status-good {
    background: rgba(34, 197, 94, 0.14);
    color: #86efac;
  }

  .status-ok {
    background: rgba(251, 191, 36, 0.16);
    color: #fde68a;
  }

  .status-risk {
    background: rgba(248, 113, 113, 0.16);
    color: #fecaca;
  }

  .timeline-transfer.risk .node {
    border-color: #f87171;
  }

  .faq-section {
    padding-top: 10px;
  }

  .faq-list {
    display: grid;
    gap: 12px;
    margin-top: 18px;
  }

  .faq-list details {
    margin: 0;
    padding: 18px 20px;
  }

  .faq-list summary {
    display: flex;
    justify-content: space-between;
    cursor: pointer;
    list-style: none;
    color: #e0f2fe;
    font-weight: 900;
  }

  .faq-list p {
    margin: 12px 0 0;
    color: #cbd5e1;
    line-height: 1.6;
  }

  .site-footer {
    width: 100%;
    border-top: 1px solid rgba(148, 163, 184, 0.18);
    background: rgba(2, 6, 23, 0.92);
    padding: 28px 0;
  }

  .footer-inner {
    display: grid;
    grid-template-columns: minmax(240px, 0.8fr) 1.2fr;
    gap: 24px;
    width: min(1120px, calc(100% - 32px));
    margin: 0 auto;
  }

  .footer-brand {
    display: flex;
    gap: 14px;
    align-items: center;
  }

  .footer-brand img {
    width: 46px;
    height: 46px;
    border-radius: 8px;
  }

  .footer-brand strong {
    display: block;
    font-size: 1.12rem;
  }

  .footer-brand p,
  .copyright {
    margin: 4px 0 0;
    color: #94a3b8;
  }

  .footer-links {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 16px;
  }

  .footer-links a {
    color: #cbd5e1;
    font-weight: 800;
    text-decoration: none;
  }

  .footer-links a:hover {
    color: #f8fafc;
    text-decoration: underline;
  }

  .footer-links a.primary-link {
    color: #fbbf24;
    font-weight: 900;
  }

  .copyright {
    grid-column: 1 / -1;
    font-size: 0.88rem;
  }

  .loader {
    width: 16px;
    height: 16px;
    margin-right: 10px;
    border: 3px solid rgba(31, 41, 55, 0.2);
    border-top-color: #1f2937;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @keyframes train-pass {
    0% {
      left: -142px;
    }

    72% {
      left: calc(100% + 142px);
    }

    100% {
      left: calc(100% + 142px);
    }
  }

  @keyframes loading-text {
    0% {
      opacity: 0;
      transform: translateY(4px);
    }

    18%,
    82% {
      opacity: 1;
      transform: translateY(0);
    }

    100% {
      opacity: 0;
      transform: translateY(-4px);
    }
  }

  @media (max-width: 980px) {
    .planner-hero {
      grid-template-columns: 1fr;
      gap: 24px;
      padding-top: 38px;
    }

    .route-option summary {
      grid-template-columns: 1fr;
    }

    .option-metrics {
      grid-template-columns: repeat(3, minmax(0, 1fr)) 28px;
    }
  }

  @media (max-width: 720px) {
    .planner-shell {
      background-attachment: scroll;
    }

    .planner-hero,
    .results-section,
    .faq-section {
      width: min(100% - 20px, 1120px);
    }

    .planner-panel {
      padding: 18px;
    }

    .panel-heading,
    .section-heading,
    .footer-inner {
      align-items: flex-start;
      grid-template-columns: 1fr;
    }

    .route-grid,
    .summary-strip,
    .transfer-grid,
    .risk-details,
    .option-metrics {
      grid-template-columns: 1fr;
    }

    .swap-button {
      width: 100%;
    }

    .route-option summary {
      padding: 18px;
    }

    .timeline {
      padding: 0 18px 22px 28px;
    }

    .footer-links {
      justify-content: flex-start;
    }
  }
</style>
