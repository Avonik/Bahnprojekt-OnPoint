<script lang="ts">
  import { onDestroy, onMount, tick } from 'svelte';

  const stations = [
    'Braunschweig Hbf',
    'Bremen Hbf',
    'Celle',
    'Emden Hbf',
    'Göttingen',
    'Hamburg Hbf',
    'Hamburg-Harburg',
    'Hameln',
    'Hannover Hbf',
    'Hildesheim Hbf',
    'Kiel Hbf',
    'Leer(Ostfriesl)',
    'Lingen(Ems)',
    'Lüneburg',
    'Magdeburg Hbf',
    'Minden(Westf)',
    'Münster(Westf) Hbf',
    'Nienburg(Weser)',
    'Oldenburg(Oldb)',
    'Osnabrück Hbf',
    'Rheine',
    'Stendal Hbf',
    'Uelzen',
    'Wolfsburg Hbf'
  ];

  let startingLocation = '';
  let endLocation = '';
  let time = '';
  let data: any;
  let onlyRegionalverkehr = false;
  let loading = false;
  let loadingMessageIndex = 0;
  let loadingTimer: ReturnType<typeof setInterval> | undefined;
  let errorMessage = '';
  let journeyDetailsRef: HTMLElement;

  const loadingMessages = [
    'Live-Verbindungen werden abgefragt',
    'Warten auf Anschlussreisende',
    'Historische Verspaetungen werden verglichen',
    'Anschluesse werden simuliert',
    'Plan-B-Routen werden gesucht',
    'Bordbistro beladen',
    'Empfehlung wird sortiert'
  ];

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
      loadingMessageIndex = (loadingMessageIndex + 1) % loadingMessages.length;
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
    if (Number.isFinite(plannedLayover)) return `${Math.round(plannedLayover)} min Umstieg`;

    const planned = minutesBetween(leg.planned_arrival, leg.planned_departure);
    return `${planned} min Umstieg`;
  }

  function connectionProbability(leg: any) {
    return Number(leg.connection_success_probability ?? (leg.layover_feasible ? 100 : 0));
  }

  function connectionStatus(leg: any) {
    const probability = connectionProbability(leg);

    if (!leg.layover_feasible || probability < 60) return { label: 'riskant', className: 'status-risk' };
    if (probability < 85) return { label: 'knapp', className: 'status-ok' };
    return { label: 'stabil', className: 'status-good' };
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
    errorMessage = '';
    data = undefined;

    if (!startingLocation || !endLocation || !time) {
      errorMessage = 'Bitte Start, Ziel und Abfahrtszeit auswählen.';
      loading = false;
      stopLoadingAnimation();
      return;
    }

    if (startingLocation === endLocation) {
      errorMessage = 'Start und Ziel müssen unterschiedlich sein.';
      loading = false;
      stopLoadingAnimation();
      return;
    }

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
        })
      });

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }

      data = await response.json();

      if (data?.journeys?.journeys?.length) {
        data.journeys.journeys.sort((a: any, b: any) =>
          Number(Boolean(b.best_journey)) - Number(Boolean(a.best_journey))
        );
      } else {
        errorMessage = 'Keine Verbindung gefunden.';
      }
    } catch (error) {
      console.error('Error sending data:', error);
      errorMessage = 'Die Route konnte nicht berechnet werden. Laufen Backend und MySQL noch?';
    } finally {
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
  <title>OnPoint. | Routenplaner</title>
</svelte:head>

<main class="planner-shell">
  <section id="plan" class="planner-hero">
    <div class="hero-copy">
      <p class="eyebrow">Historische Verspätungen. Klare Umstiege.</p>
      <h1>OnPoint. findet die Route, die nicht nur schnell aussieht.</h1>
      <p class="intro">
        Vergleiche Bahnverbindungen nach Dauer, Umstiegen und historischen Anschlussrisiken.
      </p>
    </div>

    <form class="planner-panel" onsubmit={(event) => { event.preventDefault(); sendData(); }}>
      <div class="panel-heading">
        <div>
          <p class="eyebrow">Route</p>
          <h2>Verbindung suchen</h2>
        </div>
      </div>

      <div class="route-grid">
        <label class="field">
          <span>Start</span>
          <select bind:value={startingLocation} aria-label="Startbahnhof">
            <option value="" disabled>Startbahnhof</option>
            {#each stations as station}
              <option value={station}>{station}</option>
            {/each}
          </select>
        </label>

        <button class="swap-button" type="button" onclick={swapStations} aria-label="Start und Ziel tauschen">
          ⇄
        </button>

        <label class="field">
          <span>Ziel</span>
          <select bind:value={endLocation} aria-label="Zielbahnhof">
            <option value="" disabled>Zielbahnhof</option>
            {#each stations as station}
              <option value={station}>{station}</option>
            {/each}
          </select>
        </label>
      </div>

      <label class="field departure-field">
        <span>Früheste Abfahrt</span>
        <input type="datetime-local" bind:value={time} />
      </label>

      <label class="regional-toggle">
        <input type="checkbox" bind:checked={onlyRegionalverkehr} />
        <span>Nur Regionalverkehr</span>
        <button class="help-bubble" type="button" aria-label="Erklärung Nur Regionalverkehr">
          ?
          <span class="tooltip">Schließt ICE, IC und EC aus und sucht nur Verbindungen mit Regionalverkehr, S-Bahn und ähnlichen Nahverkehrsangeboten.</span>
        </button>
      </label>

      {#if errorMessage}
        <div class="error-banner" role="alert">{errorMessage}</div>
      {/if}

      <button class="primary-action" type="submit" disabled={loading}>
        {#if loading}
          <span class="loader"></span>
          Analyse laeuft
        {:else}
          Beste Route finden
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
            <p>{loadingMessages[loadingMessageIndex]}</p>
          {/key}
        </div>
      {/if}
    </form>
  </section>

  {#if data?.journeys?.journeys?.length}
    <section id="results" class="results-section" bind:this={journeyDetailsRef}>
      <div class="section-heading">
        <div>
          <p class="eyebrow">Analyse</p>
          <h2>Gefundene Optionen</h2>
        </div>
        <div class="summary-strip">
          <div>
            <span>{data.journeys.journeys.length}</span>
            <small>Optionen</small>
          </div>
          <div>
            <span>{data.journeys.sum_tracked_trains ?? 0}</span>
            <small>getrackte Züge</small>
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
                    <span class="recommendation">Empfehlung</span>
                  {/if}
                  <strong>Option {index + 1}</strong>
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
                  <small>Erfolg</small>
                  <strong class={confidenceTone(journey.odds_of_successful_journey)}>{journey.odds_of_successful_journey} %</strong>
                </div>
                <div>
                  <small>Dauer</small>
                  <strong>{journey.duration}</strong>
                </div>
                <div>
                  <small>Erwartet</small>
                  <strong>{minutesLabel(journey.expected_total_cost_minutes)}</strong>
                </div>
                <div>
                  <small>Umstiege</small>
                  <strong>{journey.legs.length}</strong>
                </div>
                <div>
                  <small>Risikozeit</small>
                  <strong>{signedMinutesLabel(journey.risk_cost_minutes)}</strong>
                </div>
                <div>
                  <small>Startzug</small>
                  <strong>{journey.start_train}</strong>
                </div>
                <span class="open-indicator">+</span>
              </div>
            </summary>

            <div class="timeline">
              <div class="timeline-stop start">
                <span class="node"></span>
                <div>
                  <small>Start</small>
                  <strong>{startingLocation}</strong>
                  <p>{journey.start_time} mit {journey.start_train}</p>
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
                          <small>{transferLabel(leg)} · {connectionProbability(leg)} % Anschlusschance</small>
                          <strong>{leg.layover_at}</strong>
                        </div>
                        <span class={status.className}>{status.label}</span>
                      </div>
                      <div class="transfer-grid">
                        <div>
                          <small>Ankunft geplant / erwartet</small>
                          <strong>{leg.planned_arrival} / {leg.expected_arrival}</strong>
                          <span>{leg.last_train}</span>
                        </div>
                        <div>
                          <small>Weiterfahrt geplant / erwartet</small>
                          <strong>{leg.planned_departure} / {leg.expected_departure}</strong>
                          <span>{leg.next_train}</span>
                        </div>
                        <div>
                          <small>Datenpunkte</small>
                          <strong>{Number(leg.last_train_tracked ?? 0) + Number(leg.next_train_tracked ?? 0)}</strong>
                          <span>historische Treffer</span>
                        </div>
                      </div>
                      <div class="risk-details">
                        <div>
                          <small>Risikokosten</small>
                          <strong>{signedMinutesLabel(leg.connection_risk_cost_minutes)}</strong>
                          <span>{leg.connection_failure_probability} % Fehlschlag * {minutesLabel(leg.fallback_delay_minutes)} Plan-B-Verlust</span>
                        </div>
                        {#if leg.fallback_route}
                          <div>
                            <small>Plan B wenn verpasst</small>
                            <strong>{leg.fallback_route.departure_time} - {leg.fallback_route.arrival_time} mit {leg.fallback_route.start_train}</strong>
                            <span>Suche ab {leg.fallback_search_time}, {leg.fallback_route.from} -> {leg.fallback_route.to}, {leg.fallback_route.transfers} Umstiege, {signedMinutesLabel(leg.fallback_route.extra_minutes)} gegenueber Original</span>
                          </div>
                        {:else}
                          <div>
                            <small>Plan B wenn verpasst</small>
                            <strong>Keine belastbare Alternative gefunden</strong>
                            <span>Suche ab {leg.fallback_search_time}. Fuer den Score wird ein Default-Verlust von {minutesLabel(leg.fallback_delay_minutes)} verwendet.</span>
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
                    <strong>Direktverbindung ohne Umstieg</strong>
                  </div>
                </div>
              {/if}

              <div class="timeline-stop end">
                <span class="node"></span>
                <div>
                  <small>Ziel</small>
                  <strong>{endLocation}</strong>
                  <p>Ankunft {journey.end_time}</p>
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
        <h2>Häufige Fragen</h2>
      </div>
    </div>

    <div class="faq-list">
      <details>
        <summary>Wie findet OnPoint. die Verbindungen?<span>+</span></summary>
        <p>OnPoint. sucht aktuelle Bahnverbindungen und bewertet die Umstiege anschließend mit historischen Verspätungsdaten.</p>
      </details>
      <details>
        <summary>Was bedeutet die Anschlusschance?<span>+</span></summary>
        <p>Die Anschlusschance schätzt, wie wahrscheinlich ein Umstieg klappt. Dafür werden beobachtete Ankunfts- und Abfahrtsverspätungen ähnlicher Züge verglichen.</p>
      </details>
      <details>
        <summary>Warum wird nicht immer die schnellste Route empfohlen?<span>+</span></summary>
        <p>Die Empfehlung achtet nicht nur auf die reine Fahrzeit. Ein kurzer, aber riskanter Anschluss kann schlechter sein als eine etwas ruhigere Verbindung.</p>
      </details>
      <details>
        <summary>Was bedeutet Risikozeit?<span>+</span></summary>
        <p>Risikozeit zeigt, wie stark ein verpasster Anschluss die Reise voraussichtlich verzögern würde. Wenn schnell ein guter Plan B existiert, bleibt dieser Wert niedrig.</p>
      </details>
      <details>
        <summary>Was ist der Plan B?<span>+</span></summary>
        <p>Bei riskanten Umstiegen sucht OnPoint. eine mögliche Alternative ab dem Umstiegsbahnhof. So sehen Sie, was wahrscheinlich passiert, falls der Anschluss nicht klappt.</p>
      </details>
      <details>
        <summary>Kann ich direkt ein Ticket kaufen?<span>+</span></summary>
        <p>Noch nicht direkt in OnPoint. Preise, Verfügbarkeit und Buchung bleiben bei der Deutschen Bahn oder dem jeweiligen Anbieter.</p>
      </details>
    </div>
  </section>

  <footer id="sources" class="site-footer">
    <div class="footer-inner">
      <div class="footer-brand">
        <img src="/onpoint-logo.svg" alt="" />
        <div>
          <strong>OnPoint.</strong>
          <p>Ein Bahnprojekt von Julian Hermes.</p>
        </div>
      </div>
      <nav class="footer-links" aria-label="Footer links">
        <a class="primary-link" href="https://juhermes.de" target="_blank" rel="noreferrer">juhermes.de</a>
        <a class="primary-link" href="https://github.com/Avonik" target="_blank" rel="noreferrer">GitHub</a>
        <a href="https://www.bahn.de/" target="_blank" rel="noreferrer">Deutsche Bahn</a>
        <a href="https://github.com/public-transport/db-vendo-client" target="_blank" rel="noreferrer">db-vendo-client</a>
        <a href="https://github.com/FahrplanDatenGarten/pyhafas" target="_blank" rel="noreferrer">pyhafas</a>
      </nav>
      <p class="copyright">© 2026 Julian Hermes. Datenquellen: importierte historische Bahn-Dumps, Deutsche Bahn Web API, db-vendo-client/pyhafas.</p>
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
