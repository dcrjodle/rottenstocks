"""
Configuration for Database Testing Tools

This file contains configuration settings for the database testing tools.
Modify these settings to customize the behavior of the testing environment.
"""

# Default query limits
DEFAULT_QUERY_LIMIT = 20
MAX_QUERY_LIMIT = 1000

# Sample data generation defaults
DEFAULT_STOCKS_COUNT = 10
DEFAULT_EXPERTS_COUNT = 5
DEFAULT_POSTS_PER_STOCK = 20
DEFAULT_RATINGS_PER_STOCK = 3

# Performance benchmarks thresholds (in seconds)
PERFORMANCE_THRESHOLDS = {
    'fast': 0.1,      # Under 100ms is considered fast
    'acceptable': 1.0, # Under 1s is acceptable
    'slow': 5.0       # Over 5s is considered slow
}

# Health check settings
HEALTH_CHECK_RECENT_DAYS = 7
MAX_TABLE_DISPLAY_ROWS = 20

# Export settings
SUPPORTED_EXPORT_FORMATS = ['csv', 'json']
DEFAULT_EXPORT_FORMAT = 'csv'

# Database connection settings
CONNECTION_TIMEOUT = 30  # seconds
QUERY_TIMEOUT = 60      # seconds

# Logging settings
LOG_LEVEL = 'INFO'
LOG_SQL_QUERIES = False  # Set to True to log all SQL queries

# Interactive shell settings
ENABLE_IPYTHON = True    # Use IPython if available
ENABLE_AUTOCOMPLETE = True
SHELL_HISTORY_SIZE = 1000

# Sample data content settings
SOCIAL_MEDIA_PLATFORMS = ['reddit', 'twitter', 'stocktwits']
SENTIMENT_DISTRIBUTION = {
    'positive': 0.4,
    'neutral': 0.4, 
    'negative': 0.2
}

# Default stock sectors for sample data
STOCK_SECTORS = [
    'Technology',
    'Healthcare',
    'Financial Services',
    'Consumer Goods',
    'Energy',
    'Automotive',
    'Entertainment',
    'Retail',
    'Banking',
    'Telecommunications'
]