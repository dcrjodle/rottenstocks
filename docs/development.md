# RottenStocks Development Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Project Structure](#project-structure)
3. [Development Setup](#development-setup)
4. [Coding Standards](#coding-standards)
5. [Git Workflow](#git-workflow)
6. [Testing Guidelines](#testing-guidelines)
7. [Debugging & Troubleshooting](#debugging--troubleshooting)
8. [Performance Best Practices](#performance-best-practices)

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Docker and Docker Compose
- PostgreSQL 15 (via Docker)
- Redis 7 (via Docker)
- Git

### Quick Start
```bash
# Clone the repository
git clone https://github.com/yourusername/rottenstocks.git
cd rottenstocks

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys (see api-keys-guide.md)

# Start Docker services
docker-compose up -d

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head

# Frontend setup
cd ../frontend
npm install

# Run both services
# Terminal 1 - Backend
cd backend && uvicorn app.main:app --reload

# Terminal 2 - Frontend
cd frontend && npm run dev
```

## Project Structure

```
rottenstocks/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/               # API endpoints
│   │   │   ├── v1/           # API version 1
│   │   │   │   ├── endpoints/ # Route handlers
│   │   │   │   └── deps.py   # Dependencies
│   │   ├── core/             # Core functionality
│   │   │   ├── config.py     # Settings management
│   │   │   ├── security.py   # Auth & security
│   │   │   └── logging.py    # Logging config
│   │   ├── db/               # Database
│   │   │   ├── models/       # SQLAlchemy models
│   │   │   ├── repositories/ # Data access layer
│   │   │   └── session.py    # Database session
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   │   ├── reddit.py     # Reddit integration
│   │   │   ├── gemini.py     # AI sentiment analysis
│   │   │   └── stock.py      # Stock data service
│   │   ├── tasks/            # Background tasks
│   │   ├── utils/            # Utilities
│   │   └── main.py           # App entry point
│   ├── tests/                # Backend tests
│   ├── alembic/              # Database migrations
│   ├── requirements.txt      # Python dependencies
│   └── pyproject.toml        # Project config
├── frontend/                  # React frontend
│   ├── src/
│   │   ├── components/       # React components
│   │   │   ├── common/       # Shared components
│   │   │   ├── stocks/       # Stock-related
│   │   │   └── ratings/      # Rating displays
│   │   ├── pages/            # Page components
│   │   ├── hooks/            # Custom React hooks
│   │   ├── services/         # API client
│   │   ├── store/            # Zustand stores
│   │   ├── styles/           # SASS files
│   │   │   ├── base/         # Reset, variables
│   │   │   ├── components/   # Component styles
│   │   │   ├── layouts/      # Layout styles
│   │   │   └── main.scss     # Main entry
│   │   ├── types/            # TypeScript types
│   │   ├── utils/            # Utilities
│   │   └── main.tsx          # App entry
│   ├── public/               # Static assets
│   ├── tests/                # Frontend tests
│   ├── package.json          # NPM dependencies
│   └── vite.config.ts        # Vite configuration
├── docs/                     # Documentation
├── docker-compose.yml        # Local services
├── Makefile                  # Common commands
└── README.md                 # Project overview
```

## Development Setup

### Backend Development

#### Virtual Environment
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dev dependencies
```

#### Database Setup
```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Add new table"

# Seed development data
python -m app.scripts.seed_data
```

#### Running the Backend
```bash
# Development server with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# With custom settings
ENVIRONMENT=development uvicorn app.main:app --reload
```

### Frontend Development

#### Installation
```bash
cd frontend
npm install
```

#### Development Server
```bash
# Start with hot reload
npm run dev

# Start with specific port
npm run dev -- --port 3001
```

#### Building for Production
```bash
npm run build
npm run preview  # Test production build
```

## Coding Standards

### Python Code Style

#### PEP 8 Compliance
```python
# Good
def calculate_stock_rating(
    expert_score: int,
    popular_score: int,
    weight: float = 0.5
) -> dict[str, Any]:
    """Calculate weighted stock rating.
    
    Args:
        expert_score: Expert sentiment score (0-100)
        popular_score: Popular sentiment score (0-100)
        weight: Expert score weight (0-1)
        
    Returns:
        Dictionary with rating details
    """
    weighted_score = (
        expert_score * weight + 
        popular_score * (1 - weight)
    )
    return {
        "score": round(weighted_score),
        "sentiment": get_sentiment(weighted_score)
    }

# Bad
def calc_rating(e_score,p_score,w=0.5):
    score=e_score*w+p_score*(1-w)
    return {"score":round(score),"sentiment":get_sentiment(score)}
```

#### Type Hints
```python
from typing import Optional, List, Dict, Any
from datetime import datetime

# Always use type hints
async def fetch_reddit_posts(
    symbol: str,
    subreddit: Optional[str] = None,
    limit: int = 25
) -> List[Dict[str, Any]]:
    ...

# Use domain models
from app.schemas.stock import StockRating

def process_rating(rating: StockRating) -> StockRating:
    ...
```

#### Async/Await Best Practices
```python
# Good - Concurrent execution
async def get_stock_data(symbol: str) -> dict:
    # Run independent tasks concurrently
    price_task = fetch_price(symbol)
    rating_task = fetch_rating(symbol)
    social_task = fetch_social_data(symbol)
    
    price, rating, social = await asyncio.gather(
        price_task, rating_task, social_task
    )
    
    return {
        "price": price,
        "rating": rating,
        "social": social
    }

# Bad - Sequential execution
async def get_stock_data(symbol: str) -> dict:
    price = await fetch_price(symbol)
    rating = await fetch_rating(symbol)
    social = await fetch_social_data(symbol)
    ...
```

### TypeScript/React Code Style

#### Component Structure
```typescript
// Good - Functional component with proper typing
import { FC, useState, useCallback } from 'react';
import { StockData } from '@/types/stock';
import styles from './StockCard.module.scss';

interface StockCardProps {
  stock: StockData;
  onSelect?: (symbol: string) => void;
}

export const StockCard: FC<StockCardProps> = ({ stock, onSelect }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const handleClick = useCallback(() => {
    setIsExpanded(prev => !prev);
    onSelect?.(stock.symbol);
  }, [stock.symbol, onSelect]);
  
  return (
    <div className={styles.card} onClick={handleClick}>
      <h3>{stock.symbol}</h3>
      <p>{stock.name}</p>
      {isExpanded && (
        <div className={styles.details}>
          {/* Additional details */}
        </div>
      )}
    </div>
  );
};
```

#### Custom Hooks
```typescript
// hooks/useStockData.ts
import { useQuery } from '@tanstack/react-query';
import { stockApi } from '@/services/api';

export const useStockData = (symbol: string) => {
  return useQuery({
    queryKey: ['stock', symbol],
    queryFn: () => stockApi.getStock(symbol),
    staleTime: 60 * 1000, // 1 minute
    enabled: !!symbol,
  });
};
```

### SASS/SCSS Guidelines

#### File Organization
```scss
// styles/base/_variables.scss
$primary-color: #1a73e8;
$danger-color: #dc3545;
$success-color: #28a745;

$breakpoint-mobile: 576px;
$breakpoint-tablet: 768px;
$breakpoint-desktop: 1024px;

// styles/base/_mixins.scss
@mixin responsive($breakpoint) {
  @if $breakpoint == 'mobile' {
    @media (max-width: $breakpoint-mobile) {
      @content;
    }
  }
  // ... other breakpoints
}

// styles/components/StockCard.module.scss
@import '@/styles/base/variables';
@import '@/styles/base/mixins';

.card {
  padding: 1rem;
  border-radius: 8px;
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  
  @include responsive('mobile') {
    padding: 0.75rem;
  }
  
  &:hover {
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
  }
}
```

## Git Workflow

### Branch Naming
- `feature/add-stock-search` - New features
- `fix/rating-calculation` - Bug fixes
- `chore/update-dependencies` - Maintenance
- `docs/api-documentation` - Documentation

### Commit Messages
```bash
# Format: <type>(<scope>): <subject>

# Examples
feat(api): add reddit sentiment endpoint
fix(frontend): correct rating display calculation
docs(readme): update installation instructions
chore(deps): upgrade fastapi to 0.104.0

# With body for complex changes
feat(ratings): implement weighted sentiment algorithm

- Add expert weight configuration
- Include time decay for older posts
- Filter spam accounts by karma threshold

Closes #123
```

### Pull Request Process
1. Create feature branch from `main`
2. Make changes following coding standards
3. Write/update tests
4. Update documentation if needed
5. Create PR with description template
6. Ensure CI passes
7. Request review from team member
8. Merge after approval

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings
```

## Testing Guidelines

### Backend Testing

#### Unit Tests
```python
# tests/test_services/test_rating.py
import pytest
from app.services.rating import calculate_sentiment

class TestRatingService:
    @pytest.mark.parametrize("score,expected", [
        (85, "BUY"),
        (50, "HOLD"),
        (25, "SELL"),
    ])
    def test_calculate_sentiment(self, score, expected):
        result = calculate_sentiment(score)
        assert result == expected
    
    @pytest.mark.asyncio
    async def test_fetch_reddit_sentiment(self, mock_reddit_client):
        # Test async functions
        ...
```

#### Integration Tests
```python
# tests/test_api/test_stocks.py
from fastapi.testclient import TestClient

def test_get_stock_rating(client: TestClient, test_stock):
    response = client.get(f"/api/v1/stocks/{test_stock.symbol}/rating")
    assert response.status_code == 200
    data = response.json()
    assert "expert_score" in data
    assert "popular_score" in data
```

### Frontend Testing

#### Component Tests
```typescript
// tests/components/StockCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { StockCard } from '@/components/stocks/StockCard';

describe('StockCard', () => {
  const mockStock = {
    symbol: 'AAPL',
    name: 'Apple Inc.',
    price: 150.00,
  };
  
  it('renders stock information', () => {
    render(<StockCard stock={mockStock} />);
    
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
  });
  
  it('expands on click', () => {
    render(<StockCard stock={mockStock} />);
    
    const card = screen.getByRole('article');
    fireEvent.click(card);
    
    expect(screen.getByTestId('stock-details')).toBeVisible();
  });
});
```

### Running Tests
```bash
# Backend
cd backend
pytest                          # Run all tests
pytest -v                       # Verbose output
pytest tests/test_api/         # Specific directory
pytest -k "test_rating"        # Tests matching pattern
pytest --cov=app              # With coverage

# Frontend
cd frontend
npm test                       # Run all tests
npm test -- --watch           # Watch mode
npm test -- --coverage        # With coverage
```

## Debugging & Troubleshooting

### Common Issues

#### Backend Issues

1. **Database Connection Errors**
```bash
# Check PostgreSQL is running
docker-compose ps

# Check connection string
echo $DATABASE_URL

# Test connection
python -c "from app.db.session import engine; engine.connect()"
```

2. **Migration Failures**
```bash
# Check migration history
alembic history

# Downgrade if needed
alembic downgrade -1

# Reset database (development only!)
alembic downgrade base
alembic upgrade head
```

3. **API Key Errors**
```python
# Debug API keys
from app.core.config import get_settings
settings = get_settings()
print(f"Reddit configured: {bool(settings.reddit_client_id)}")
print(f"Gemini configured: {bool(settings.google_gemini_api_key)}")
```

#### Frontend Issues

1. **Build Errors**
```bash
# Clear cache
rm -rf node_modules package-lock.json
npm install

# Check for type errors
npm run type-check

# Check for lint errors
npm run lint
```

2. **API Connection Issues**
```typescript
// Check API URL in development
console.log('API URL:', import.meta.env.VITE_API_URL);

// Enable request logging
axios.interceptors.request.use(request => {
  console.log('Starting Request:', request);
  return request;
});
```

### Debugging Tools

#### Backend Debugging
```python
# Use debugger
import pdb; pdb.set_trace()

# Or with IPython
import IPython; IPython.embed()

# FastAPI debug mode
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", reload=True, log_level="debug")
```

#### Frontend Debugging
```typescript
// React Developer Tools
// Install browser extension

// Redux DevTools (if using Redux)
const store = createStore(
  rootReducer,
  window.__REDUX_DEVTOOLS_EXTENSION__ && window.__REDUX_DEVTOOLS_EXTENSION__()
);

// Performance profiling
import { Profiler } from 'react';

<Profiler id="StockList" onRender={onRenderCallback}>
  <StockList />
</Profiler>
```

## Performance Best Practices

### Backend Performance

1. **Database Optimization**
```python
# Use select_related for foreign keys
stocks = db.query(Stock).options(
    selectinload(Stock.ratings)
).all()

# Index frequently queried fields
class Stock(Base):
    symbol = Column(String, index=True)
    created_at = Column(DateTime, index=True)
```

2. **Caching Strategy**
```python
from app.core.cache import cache

@cache(expire=300)  # 5 minutes
async def get_stock_rating(symbol: str):
    # Expensive operation
    ...
```

3. **Background Tasks**
```python
from app.tasks import celery_app

@celery_app.task
def analyze_sentiment(post_id: str):
    # Long-running task
    ...
```

### Frontend Performance

1. **Code Splitting**
```typescript
// Lazy load routes
const StockDetail = lazy(() => import('./pages/StockDetail'));

// Lazy load heavy components
const ChartComponent = lazy(() => import('./components/Chart'));
```

2. **Memoization**
```typescript
// Memoize expensive calculations
const expensiveValue = useMemo(() => {
  return calculateComplexValue(data);
}, [data]);

// Memoize callbacks
const handleClick = useCallback((id: string) => {
  // Handle click
}, []);
```

3. **Virtual Scrolling**
```typescript
// For large lists
import { VirtualList } from '@tanstack/react-virtual';
```

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [SASS Guidelines](https://sass-guidelin.es/)
- [Reddit API Documentation](https://www.reddit.com/dev/api)
- [Google Gemini API](https://ai.google.dev/)

## Getting Help

1. Check existing documentation in `/docs`
2. Search closed issues on GitHub
3. Ask in team Slack channel
4. Create detailed issue with reproduction steps