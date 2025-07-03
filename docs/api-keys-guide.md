# API Keys Management Guide

## Overview

This guide explains how RottenStocks manages API keys for external services across different environments.

## Required API Keys

### 1. Reddit API
- **Purpose**: Fetch posts from finance subreddits for popular sentiment analysis
- **Sign up**: https://www.reddit.com/prefs/apps
- **Type**: OAuth2 App (script type for backend)
- **Required values**:
  - `REDDIT_CLIENT_ID`: Your app's client ID
  - `REDDIT_CLIENT_SECRET`: Your app's secret
  - `REDDIT_USER_AGENT`: Format: "RottenStocks/1.0 by YourRedditUsername"

### 2. Alpha Vantage API
- **Purpose**: Real-time stock price data and company information
- **Sign up**: https://www.alphavantage.co/support/#api-key
- **Free tier**: 5 API requests per minute, 500 per day
- **Required values**:
  - `ALPHA_VANTAGE_API_KEY`: Your API key

### 3. Google Gemini API
- **Purpose**: AI-powered sentiment analysis of social media posts
- **Sign up**: https://makersuite.google.com/app/apikey
- **Free tier**: gemini-1.5-flash model has generous free limits
- **Required values**:
  - `GOOGLE_GEMINI_API_KEY`: Your API key

## Environment-Specific Configuration

### Development Environment

1. **File Structure**:
   ```
   rottenstocks/
   ├── .env              # Your local environment (git ignored)
   ├── .env.example      # Template for developers
   └── .gitignore        # Must include .env
   ```

2. **`.env.example` Template**:
   ```bash
   # External API Keys
   REDDIT_CLIENT_ID=your_reddit_client_id_here
   REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
   REDDIT_USER_AGENT=RottenStocks/1.0 by YourUsername
   
   ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
   
   GOOGLE_GEMINI_API_KEY=your_gemini_api_key_here
   
   # Database
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rottenstocks
   
   # Redis
   REDIS_URL=redis://localhost:6379
   
   # Security
   JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
   
   # Application
   DEBUG=true
   ENVIRONMENT=development
   ```

3. **Loading in Python**:
   ```python
   # backend/app/core/config.py
   from pydantic_settings import BaseSettings
   from functools import lru_cache
   
   class Settings(BaseSettings):
       # Reddit API
       reddit_client_id: str
       reddit_client_secret: str
       reddit_user_agent: str
       
       # Alpha Vantage
       alpha_vantage_api_key: str
       
       # Google Gemini
       google_gemini_api_key: str
       
       # Database
       database_url: str
       
       # Redis
       redis_url: str
       
       # Security
       jwt_secret_key: str
       
       # Application
       debug: bool = False
       environment: str = "production"
       
       class Config:
           env_file = ".env"
           case_sensitive = False
   
   @lru_cache()
   def get_settings():
       return Settings()
   ```

### Production Environment

1. **Environment Variables**:
   - Set directly in hosting platform (Railway, Heroku, AWS, etc.)
   - Use secrets management service for sensitive keys

2. **Recommended Services**:
   - **AWS**: AWS Secrets Manager or Parameter Store
   - **Google Cloud**: Secret Manager
   - **Azure**: Key Vault
   - **Self-hosted**: HashiCorp Vault

3. **Docker Production Setup**:
   ```dockerfile
   # backend/Dockerfile
   FROM python:3.11-slim
   
   # Don't include .env in production image
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY ./app ./app
   
   # Keys come from environment at runtime
   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

4. **Docker Compose Production**:
   ```yaml
   # docker-compose.prod.yml
   version: '3.8'
   services:
     backend:
       image: rottenstocks-backend:latest
       environment:
         - REDDIT_CLIENT_ID=${REDDIT_CLIENT_ID}
         - REDDIT_CLIENT_SECRET=${REDDIT_CLIENT_SECRET}
         - REDDIT_USER_AGENT=${REDDIT_USER_AGENT}
         - ALPHA_VANTAGE_API_KEY=${ALPHA_VANTAGE_API_KEY}
         - GOOGLE_GEMINI_API_KEY=${GOOGLE_GEMINI_API_KEY}
         - DATABASE_URL=${DATABASE_URL}
         - REDIS_URL=${REDIS_URL}
         - JWT_SECRET_KEY=${JWT_SECRET_KEY}
         - ENVIRONMENT=production
   ```

## Security Best Practices

### 1. Never Commit Secrets
```gitignore
# .gitignore
.env
.env.*
!.env.example
```

### 2. Rotate Keys Regularly
- Set up key rotation schedule (quarterly recommended)
- Use multiple keys when possible (primary/secondary)
- Implement graceful key rotation without downtime

### 3. Limit Key Permissions
- Reddit: Use read-only OAuth scope
- Create service-specific API keys when possible
- Monitor API key usage for anomalies

### 4. Key Validation on Startup
```python
# backend/app/core/startup.py
import sys
from app.core.config import get_settings

def validate_api_keys():
    """Validate all required API keys are present"""
    settings = get_settings()
    required_keys = [
        ('reddit_client_id', 'Reddit Client ID'),
        ('reddit_client_secret', 'Reddit Client Secret'),
        ('alpha_vantage_api_key', 'Alpha Vantage API Key'),
        ('google_gemini_api_key', 'Google Gemini API Key'),
    ]
    
    missing = []
    for key, name in required_keys:
        if not getattr(settings, key, None):
            missing.append(name)
    
    if missing:
        print(f"ERROR: Missing required API keys: {', '.join(missing)}")
        sys.exit(1)
```

## Reddit API Specific Setup

### 1. Creating Reddit App
1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Fill in:
   - Name: RottenStocks
   - App type: **script** (for backend use)
   - Description: Stock sentiment analysis platform
   - About URL: https://rottenstocks.com/about
   - Redirect URI: http://localhost:8000/auth/reddit/callback (for dev)
4. Save the client ID and secret

### 2. Reddit API Rate Limits
- **OAuth authenticated**: 60 requests per minute
- **Burst limit**: Allow short bursts up to 100 requests
- **Best practice**: Implement exponential backoff

### 3. Accessing Reddit Data
```python
# backend/app/services/reddit_service.py
import asyncpraw
from app.core.config import get_settings

async def create_reddit_client():
    settings = get_settings()
    return asyncpraw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent=settings.reddit_user_agent
    )

async def fetch_subreddit_posts(symbol: str, subreddit: str = "all"):
    reddit = await create_reddit_client()
    
    # Target subreddits for stock discussions
    target_subreddits = [
        "wallstreetbets",
        "stocks", 
        "investing",
        "StockMarket",
        "SecurityAnalysis"
    ]
    
    if subreddit == "all":
        subreddit_str = "+".join(target_subreddits)
    else:
        subreddit_str = subreddit
    
    subreddit_obj = await reddit.subreddit(subreddit_str)
    
    posts = []
    async for post in subreddit_obj.search(
        f"${symbol} OR {symbol}", 
        time_filter="day", 
        limit=25
    ):
        posts.append({
            "id": post.id,
            "title": post.title,
            "content": post.selftext,
            "score": post.score,
            "num_comments": post.num_comments,
            "created_utc": post.created_utc,
            "subreddit": post.subreddit.display_name,
            "author": str(post.author) if post.author else "[deleted]",
            "url": post.url,
            "upvote_ratio": post.upvote_ratio
        })
    
    return posts
```

## Testing with Mock Keys

For testing, create a `.env.test` file:
```bash
# .env.test
REDDIT_CLIENT_ID=test_client_id
REDDIT_CLIENT_SECRET=test_client_secret
REDDIT_USER_AGENT=TestBot/1.0
ALPHA_VANTAGE_API_KEY=test_av_key
GOOGLE_GEMINI_API_KEY=test_gemini_key
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rottenstocks_test
REDIS_URL=redis://localhost:6379/1
JWT_SECRET_KEY=test_jwt_secret
ENVIRONMENT=test
```

## Monitoring API Usage

1. **Track API calls**: Log each external API request
2. **Monitor rate limits**: Alert before hitting limits
3. **Cost tracking**: Monitor usage against free tiers
4. **Error tracking**: Alert on API failures

## Troubleshooting

### Common Issues

1. **"API key not found" error**:
   - Check `.env` file exists and is in correct location
   - Verify key names match exactly (case-sensitive)
   - Ensure no extra spaces or quotes in values

2. **Reddit 401 Unauthorized**:
   - Verify client ID and secret are correct
   - Check user agent format
   - Ensure app type is "script" for backend use

3. **Rate limit errors**:
   - Implement caching to reduce API calls
   - Add request queuing with delays
   - Use Redis to track API usage

4. **Production keys not loading**:
   - Verify environment variables are set
   - Check for typos in variable names
   - Ensure deployment platform supports env vars