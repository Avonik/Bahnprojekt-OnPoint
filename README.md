# OnPoint.

Journey planner for German train routes with historical transfer reliability, expected delay simulation, and Plan-B route estimates.

## Project Layout

- `filedforBahnprojekt/backend.py` - Flask API and route scoring.
- `filedforBahnprojekt/scrape_train_data.py` - station-board scraper for historical MySQL data.
- `filedforBahnprojekt/connection_model.py` - statistical transfer model.
- `filedforBahnprojekt/my-app/` - SvelteKit frontend.

