# OnPoint.

Journey planner for German train routes with historical transfer reliability, expected delay simulation, and Plan-B route estimates.

## Project Layout

- `filedforBahnprojekt/backend.py` - Flask API and route scoring.
- `filedforBahnprojekt/scrape_train_data.py` - station-board scraper for historical MySQL data.
- `filedforBahnprojekt/connection_model.py` - statistical transfer model.
- `filedforBahnprojekt/my-app/` - SvelteKit frontend.

## Local Setup

Create `filedforBahnprojekt/.env` from `filedforBahnprojekt/.env.example` and fill in your local MySQL credentials.

```powershell
cd C:\Users\julia\PythonProject\BahnProjekt\filedforBahnprojekt
..\.venv\Scripts\pip.exe install -r requirements.txt
..\.venv\Scripts\python.exe backend.py
```

In a second terminal:

```powershell
cd C:\Users\julia\PythonProject\BahnProjekt\filedforBahnprojekt\my-app
npm.cmd install
npm.cmd run dev
```

The frontend calls `/api/submit`. In development, Vite proxies `/api` to Flask on `http://localhost:5000`.

## Database

Do not commit database dumps or `.env` files. The repository ignores SQL dumps, archives, local databases, virtual environments, and Node build artifacts.

For deployment, import a fresh MySQL dump on the server and set the same `TRAINDB_*` environment variables there.
