# OnPoint frontend

The SvelteKit user interface for OnPoint. It lets users search for a journey, compare route alternatives and inspect transfer probabilities, expected delays and Plan-B connections.

For the project concept, architecture and backend setup, see the [main README](../../README.md).

## Development

Install dependencies and start Vite:

```bash
npm ci
npm run dev
```

The development server proxies requests from `/api` to the Flask backend at `http://localhost:5000`. Start `onpoint/backend.py` separately before running a complete journey analysis.

## Quality checks

```bash
npm run check
npm run build
```

`npm run check` runs Svelte and TypeScript diagnostics. `npm run build` creates the production bundle.

## Routes

- `/` redirects to the planner;
- `/planner` contains the complete OnPoint experience;
- the SvelteKit error page links users back to the planner.

## Main files

- `src/routes/planner/+page.svelte` — search, results and explanatory content;
- `src/routes/+layout.svelte` — shared navigation and language switch;
- `src/lib/i18n.ts` — persisted German/English language selection;
- `src/app.css` — global design system;
- `static/onpoint-logo.svg` — application logo.
