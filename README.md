# RottenStocks 📈

A stock rating platform that provides dual sentiment ratings (expert and popular opinion) similar to Rotten Tomatoes for movies. RottenStocks analyzes social media sentiment to generate actionable buy/sell recommendations.

## 🎯 Project Description

RottenStocks combines the power of social media sentiment analysis with expert opinions to provide comprehensive stock ratings. The platform aggregates data from Reddit finance communities and applies AI-powered sentiment analysis to help investors make informed decisions.

### Key Features

- **Dual Rating System**: Expert vs Popular opinion ratings (0-100 scale)
- **Social Media Integration**: Real-time sentiment from Reddit finance communities
- **AI-Powered Analysis**: Google Gemini for intelligent sentiment analysis
- **Real-Time Data**: Live stock prices and rating updates
- **Interactive Dashboard**: Clean, responsive interface built with React

### Technology Stack

- **Frontend**: React 18 + TypeScript + Vite + Custom SASS
- **Backend**: FastAPI (Python 3.11+) + SQLAlchemy + PostgreSQL
- **AI/ML**: Google Gemini (gemini-1.5-flash) for sentiment analysis
- **Data Sources**: Reddit API, Alpha Vantage (stock data)
- **Caching**: Redis for performance optimization

## 📋 Prerequisites

Before setting up RottenStocks, ensure you have the following installed:

### Required Software
- **Python 3.11+** - Backend development
- **Node.js 18+** and **npm** - Frontend development
- **Docker** and **Docker Compose** - Database and services
- **Git** - Version control

### API Keys Required
You'll need to obtain API keys from these services:

1. **Reddit API**
   - Sign up at: https://www.reddit.com/prefs/apps
   - Create a "script" type application
   - Note down: Client ID, Client Secret

2. **Alpha Vantage API** (Stock Data)
   - Sign up at: https://www.alphavantage.co/support/#api-key
   - Free tier: 5 requests/minute, 500/day

3. **Google Gemini API** (AI Analysis)
   - Sign up at: https://makersuite.google.com/app/apikey
   - Free tier with generous limits for gemini-1.5-flash

## ⚙️ Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/rottenstocks.git
cd rottenstocks
```

### 2. Environment Configuration
```bash
# Copy the environment template
cp .env.example .env

# Edit .env file with your API keys
nano .env  # or use your preferred editor
```

**Required environment variables:**
```bash
# External API Keys
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=RottenStocks/1.0 by YourUsername

ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key

GOOGLE_GEMINI_API_KEY=your_gemini_api_key

# Database (default values for local development)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rottenstocks
REDIS_URL=redis://localhost:6379

# Security
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
```

### 3. Start Docker Services
```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 4. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# (Optional) Seed with sample data
python -m app.scripts.seed_data
```

### 5. Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

## 🚀 Start Guide

### Development Mode

You'll need three terminal windows/tabs:

#### Terminal 1: Docker Services
```bash
# Start PostgreSQL and Redis
docker-compose up -d

# View logs (optional)
docker-compose logs -f
```

#### Terminal 2: Backend Server
```bash
cd backend
source venv/bin/activate  # Activate virtual environment
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend API will be available at: http://localhost:8000

- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Health Check**: http://localhost:8000/health

#### Terminal 3: Frontend Server
```bash
cd frontend
npm run dev
```

The frontend will be available at: http://localhost:5173

### Quick Verification

1. **Backend Health**: Visit http://localhost:8000/health
2. **API Docs**: Visit http://localhost:8000/docs
3. **Frontend**: Visit http://localhost:5173
4. **Database**: Check `docker-compose ps` shows postgres and redis as healthy

### Common Commands

```bash
# Backend
cd backend
python -m pytest                    # Run tests
ruff check .                        # Lint code
ruff format .                       # Format code
alembic revision --autogenerate -m "description"  # Create migration

# Frontend
cd frontend
npm test                            # Run tests
npm run lint                        # Lint code
npm run build                       # Build for production
npm run preview                     # Preview production build

# Docker
docker-compose up -d                # Start services
docker-compose down                 # Stop services
docker-compose logs -f              # View logs
```

## 📚 Documentation

Comprehensive documentation is available in the `/docs` folder:

- **[Architecture](docs/architecture.md)** - System design and components
- **[API Specification](docs/api-spec.yaml)** - OpenAPI 3.0 specification
- **[Development Guide](docs/development-guide.md)** - Detailed development workflow
- **[API Keys Guide](docs/api-keys-guide.md)** - API key management and security
- **[Implementation Guide](docs/implementation.md)** - Phase-by-phase implementation plan

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow the coding standards in the [Development Guide](docs/development-guide.md)
4. Commit changes (`git commit -m 'feat: add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 🔧 Troubleshooting

### Common Issues

**"Database connection failed"**
- Ensure Docker services are running: `docker-compose ps`
- Check DATABASE_URL in .env file

**"API key not found"**
- Verify .env file exists and contains all required keys
- Check for typos in environment variable names

**"Frontend can't connect to API"**
- Ensure backend is running on port 8000
- Check CORS configuration in backend

**"Reddit API 401 Unauthorized"**
- Verify Reddit app is configured as "script" type
- Check client ID and secret are correct

For more detailed troubleshooting, see the [Development Guide](docs/development-guide.md#debugging--troubleshooting).

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Reddit API** for social media sentiment data
- **Alpha Vantage** for stock market data
- **Google Gemini** for AI-powered sentiment analysis
- **FastAPI** and **React** communities for excellent frameworks