# RottenStocks Architecture

## Overview

RottenStocks is a stock rating platform that provides dual sentiment ratings (expert and popular opinion) similar to how Rotten Tomatoes rates movies. The platform aggregates social media data, analyzes sentiment using AI, and presents actionable buy/sell recommendations.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React SPA)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │Stock Browser│  │Rating Display│  │Analytics Dashboard      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTPS/JSON
┌─────────────────────────────┴───────────────────────────────────┐
│                      Backend API (FastAPI)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │Stock Service │  │Rating Service│  │Social Media        │   │
│  │              │  │              │  │Aggregator          │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
│  ┌──────────────────────────┐  ┌────────────────────────────┐ │
│  │AI Analysis Service        │  │Background Job Queue        │ │
│  └──────────────────────────┘  └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
           │                │                    │
┌──────────┴────┐  ┌────────┴────────┐  ┌──────┴──────────┐
│  PostgreSQL   │  │     Redis       │  │External APIs    │
│  - Stocks     │  │  - Cache        │  │- Alpha Vantage  │
│  - Ratings    │  │  - Rate Limit   │  │- Twitter        │
│  - Users      │  │  - Job Queue    │  │- Reddit         │
│  - Experts    │  │                 │  │- Google Gemini  │
└───────────────┘  └─────────────────┘  └─────────────────┘
```

## Technology Stack

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Custom SASS/SCSS
- **State Management**: Zustand
- **API Client**: Axios with React Query
- **Routing**: React Router v6
- **Charts**: Recharts
- **Testing**: Jest + React Testing Library

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **ORM**: SQLAlchemy 2.0
- **Validation**: Pydantic v2
- **Task Queue**: Celery with Redis
- **API Documentation**: OpenAPI/Swagger
- **Testing**: pytest + pytest-asyncio

### Database & Storage
- **Primary Database**: PostgreSQL 15
- **Cache**: Redis 7
- **File Storage**: Local filesystem (development), S3 (production)

### External Services
- **Stock Data**: Alpha Vantage API
- **Social Media**: 
  - Twitter API v2
  - Reddit API
- **AI/ML**: Google Gemini (gemini-1.5-flash) for sentiment analysis
- **Monitoring**: Sentry (errors), Prometheus (metrics)

## Core Components

### 1. Stock Service
Manages stock information and real-time price data.

**Responsibilities:**
- Fetch and cache stock data from Alpha Vantage
- Provide stock search and filtering
- Manage watchlists
- Handle real-time price updates

### 2. Rating Service
Calculates and manages dual rating system.

**Responsibilities:**
- Calculate expert ratings from verified accounts
- Calculate popular ratings from general sentiment
- Provide rating history and trends
- Generate buy/sell recommendations

### 3. Social Media Aggregator
Collects and processes social media data.

**Responsibilities:**
- Fetch tweets mentioning stock symbols
- Collect Reddit posts from finance subreddits
- Filter and deduplicate content
- Queue content for sentiment analysis

### 4. AI Analysis Service
Performs sentiment analysis on social media content.

**Responsibilities:**
- Analyze text sentiment using Google Gemini
- Classify content as positive/negative/neutral
- Extract key insights and themes
- Handle rate limiting and retries

### 5. Background Job Queue
Manages asynchronous tasks.

**Tasks:**
- Periodic social media data collection
- Batch sentiment analysis
- Rating recalculation
- Cache warming
- Data cleanup

## Data Models

### Stock
```python
- id: UUID
- symbol: str (e.g., "AAPL")
- name: str
- sector: str
- market_cap: decimal
- current_price: decimal
- price_updated_at: datetime
- created_at: datetime
- updated_at: datetime
```

### Rating
```python
- id: UUID
- stock_id: UUID
- expert_score: int (0-100)
- popular_score: int (0-100)
- expert_sentiment: enum (BUY, HOLD, SELL)
- popular_sentiment: enum (BUY, HOLD, SELL)
- expert_post_count: int
- popular_post_count: int
- calculated_at: datetime
- created_at: datetime
```

### Expert
```python
- id: UUID
- name: str
- platform: enum (TWITTER, REDDIT)
- platform_username: str
- verification_status: enum
- follower_count: int
- expertise_areas: list[str]
- created_at: datetime
```

### SocialPost
```python
- id: UUID
- platform: enum
- platform_id: str
- author_username: str
- content: text
- stock_mentions: list[str]
- sentiment_score: float (-1 to 1)
- engagement_metrics: json
- posted_at: datetime
- analyzed_at: datetime
```

## API Design

### RESTful Endpoints

```
GET    /api/v1/stocks                 # List stocks with pagination
GET    /api/v1/stocks/{symbol}        # Get stock details
GET    /api/v1/stocks/{symbol}/rating # Get current rating
GET    /api/v1/stocks/{symbol}/history # Rating history

GET    /api/v1/experts                # List verified experts
GET    /api/v1/trending              # Trending stocks

GET    /api/v1/search                # Search stocks
GET    /api/v1/watchlist            # User's watchlist
POST   /api/v1/watchlist            # Add to watchlist
DELETE /api/v1/watchlist/{symbol}   # Remove from watchlist
```

### WebSocket Endpoints

```
WS /ws/stocks/{symbol}    # Real-time price updates
WS /ws/ratings/{symbol}   # Real-time rating updates
```

## Security Considerations

### Authentication & Authorization
- JWT tokens for API authentication
- OAuth2 for social login
- Rate limiting per user/IP
- API key rotation for external services

### Data Security
- Encrypt sensitive data at rest
- Use HTTPS for all communications
- Sanitize user inputs
- Implement CORS properly
- Regular security audits

### API Security
- Rate limiting on all endpoints
- Request validation
- SQL injection prevention via ORM
- XSS prevention in frontend

## Scalability Strategy

### Horizontal Scaling
- Stateless API servers behind load balancer
- Read replicas for PostgreSQL
- Redis cluster for caching
- Kubernetes for container orchestration

### Performance Optimization
- Database query optimization
- Aggressive caching strategy
- CDN for static assets
- Lazy loading in frontend
- Background job processing

### Monitoring & Observability
- Application Performance Monitoring (APM)
- Distributed tracing
- Centralized logging
- Custom business metrics
- Alerting for critical issues

## Development Workflow

### Local Development
1. Docker Compose for all services
2. Hot reloading for frontend and backend
3. Seeded test data
4. Mock external APIs option

### Testing Strategy
- Unit tests: 80%+ coverage
- Integration tests for API endpoints
- E2E tests for critical user flows
- Performance testing for high-traffic scenarios
- Security testing

### Deployment Pipeline
1. GitHub Actions for CI/CD
2. Automated testing on PR
3. Staging environment deployment
4. Production deployment with rollback
5. Post-deployment monitoring

## Future Considerations

### Phase 2 Features
- Mobile applications (React Native)
- Advanced analytics dashboard
- Portfolio tracking
- Social features (follow experts)
- Custom alerts

### Technical Improvements
- GraphQL API option
- Machine learning model training
- Real-time streaming architecture
- Multi-region deployment
- Blockchain integration for transparency