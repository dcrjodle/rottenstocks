# Stock Portfolio App

Simple stock management system with SQLite3 database, FastAPI backend, and React frontend.

## Quick Start

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python init_db.py
python -m uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm start
```

### E2E Tests
```bash
cd frontend
npx playwright install chromium
npx playwright test
```

## What's Included

- **Backend**: FastAPI REST API with SQLite3 database
- **Frontend**: React app with StockCard component
- **Database**: Pre-seeded with 3 stocks (Apple, Microsoft, NVIDIA)
- **Tests**: 8 E2E tests covering full user journey

## API Endpoints

- `GET /stocks` - Get all stocks
- `GET /stocks/{id}` - Get single stock
- `POST /stocks` - Create new stock
- `PUT /stocks/{id}` - Update stock
- `DELETE /stocks/{id}` - Delete stock

## Tech Stack

- **Backend**: Python 3.13, FastAPI, SQLite3, Uvicorn
- **Frontend**: React 18, TypeScript, Custom hooks, CSS Grid
- **Testing**: Playwright E2E tests
- **Database**: SQLite3 with real stock data