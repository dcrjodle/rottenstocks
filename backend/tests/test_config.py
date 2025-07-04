"""
Tests for configuration management.

Tests settings validation, environment loading, and configuration utilities.
"""

import os
import pytest
from unittest.mock import patch

from app.core.config import Settings, get_settings, validate_environment


class TestSettings:
    """Test the Settings class."""
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        with patch.dict(os.environ, {
            'REDDIT_CLIENT_ID': 'test_id',
            'REDDIT_CLIENT_SECRET': 'test_secret', 
            'REDDIT_USER_AGENT': 'TestBot/1.0',
            'ALPHA_VANTAGE_API_KEY': 'test_av_key',
            'GOOGLE_GEMINI_API_KEY': 'test_gemini_key',
        }, clear=True):
            settings = Settings()
            
            assert settings.PROJECT_NAME == "RottenStocks API"
            assert settings.VERSION == "1.0.0"
            assert settings.ENVIRONMENT == "development"
            assert settings.DEBUG is True
            assert settings.API_V1_PREFIX == "/api/v1"
            assert settings.HOST == "0.0.0.0"
            assert settings.PORT == 8000
    
    def test_required_fields_missing(self):
        """Test that missing required fields raise validation errors."""
        # Create a temporary Settings class with no env_file
        class TestSettings(Settings):
            class Config:
                env_file = None
                case_sensitive = True
                extra = "ignore"
        
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(Exception):  # ValidationError from pydantic
                TestSettings()
    
    def test_required_fields_present(self):
        """Test that all required fields can be set."""
        env_vars = {
            'REDDIT_CLIENT_ID': 'test_reddit_id',
            'REDDIT_CLIENT_SECRET': 'test_reddit_secret',
            'REDDIT_USER_AGENT': 'TestBot/1.0 by TestUser',
            'ALPHA_VANTAGE_API_KEY': 'test_alpha_key',
            'GOOGLE_GEMINI_API_KEY': 'test_gemini_key',
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            assert settings.REDDIT_CLIENT_ID == 'test_reddit_id'
            assert settings.REDDIT_CLIENT_SECRET == 'test_reddit_secret'
            assert settings.REDDIT_USER_AGENT == 'TestBot/1.0 by TestUser'
            assert settings.ALPHA_VANTAGE_API_KEY == 'test_alpha_key'
            assert settings.GOOGLE_GEMINI_API_KEY == 'test_gemini_key'
    
    def test_cors_origins_parsing(self):
        """Test CORS origins parsing from JSON string."""
        # Create a temporary Settings class with no env_file
        class TestSettings(Settings):
            class Config:
                env_file = None
                case_sensitive = True
                extra = "ignore"
        
        env_vars = {
            'REDDIT_CLIENT_ID': 'test_id',
            'REDDIT_CLIENT_SECRET': 'test_secret',
            'REDDIT_USER_AGENT': 'TestBot/1.0',
            'ALPHA_VANTAGE_API_KEY': 'test_av_key',
            'GOOGLE_GEMINI_API_KEY': 'test_gemini_key',
            'BACKEND_CORS_ORIGINS': '["http://localhost:3000", "http://localhost:5173"]',
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = TestSettings()
            cors_origins = settings.get_cors_origins()
            
            assert len(cors_origins) == 2
            assert 'http://localhost:3000/' in cors_origins
            assert 'http://localhost:5173/' in cors_origins
    
    def test_database_url_assembly(self):
        """Test database URL assembly from components."""
        env_vars = {
            'REDDIT_CLIENT_ID': 'test_id',
            'REDDIT_CLIENT_SECRET': 'test_secret',
            'REDDIT_USER_AGENT': 'TestBot/1.0',
            'ALPHA_VANTAGE_API_KEY': 'test_av_key',
            'GOOGLE_GEMINI_API_KEY': 'test_gemini_key',
            'POSTGRES_SERVER': 'localhost',
            'POSTGRES_USER': 'testuser',
            'POSTGRES_PASSWORD': 'testpass',
            'POSTGRES_DB': 'testdb',
            'POSTGRES_PORT': '5432',
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            assert settings.DATABASE_URL is not None
            db_url_str = str(settings.DATABASE_URL)
            assert 'postgresql+asyncpg' in db_url_str
            assert 'testuser' in db_url_str
            assert 'testpass' in db_url_str
            assert 'localhost' in db_url_str
            assert 'testdb' in db_url_str
    
    def test_redis_url_assembly(self):
        """Test Redis URL assembly from components."""
        env_vars = {
            'REDDIT_CLIENT_ID': 'test_id',
            'REDDIT_CLIENT_SECRET': 'test_secret',
            'REDDIT_USER_AGENT': 'TestBot/1.0',
            'ALPHA_VANTAGE_API_KEY': 'test_av_key',
            'GOOGLE_GEMINI_API_KEY': 'test_gemini_key',
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6379',
            'REDIS_DB': '0',
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            assert settings.REDIS_URL == 'redis://localhost:6379/0'
    
    def test_environment_properties(self):
        """Test environment detection properties."""
        # Create a temporary Settings class with no env_file
        class TestSettings(Settings):
            class Config:
                env_file = None
                case_sensitive = True
                extra = "ignore"
        
        env_vars = {
            'REDDIT_CLIENT_ID': 'test_id',
            'REDDIT_CLIENT_SECRET': 'test_secret',
            'REDDIT_USER_AGENT': 'TestBot/1.0',
            'ALPHA_VANTAGE_API_KEY': 'test_av_key',
            'GOOGLE_GEMINI_API_KEY': 'test_gemini_key',
        }
        
        # Test development
        with patch.dict(os.environ, {**env_vars, 'ENVIRONMENT': 'development'}, clear=True):
            settings = TestSettings()
            assert settings.is_development is True
            assert settings.is_production is False
            assert settings.is_testing is False
        
        # Test production
        with patch.dict(os.environ, {**env_vars, 'ENVIRONMENT': 'production'}, clear=True):
            settings = TestSettings()
            assert settings.is_development is False
            assert settings.is_production is True
            assert settings.is_testing is False
        
        # Test testing
        with patch.dict(os.environ, {**env_vars, 'TESTING': 'true'}, clear=True):
            settings = TestSettings()
            assert settings.is_development is False
            assert settings.is_production is False
            assert settings.is_testing is True


class TestConfigFunctions:
    """Test configuration utility functions."""
    
    def test_get_settings_caching(self):
        """Test that get_settings returns cached instance."""
        with patch.dict(os.environ, {
            'REDDIT_CLIENT_ID': 'test_id',
            'REDDIT_CLIENT_SECRET': 'test_secret',
            'REDDIT_USER_AGENT': 'TestBot/1.0',
            'ALPHA_VANTAGE_API_KEY': 'test_av_key',
            'GOOGLE_GEMINI_API_KEY': 'test_gemini_key',
        }, clear=True):
            settings1 = get_settings()
            settings2 = get_settings()
            
            # Should be the same instance (cached)
            assert settings1 is settings2
    
    def test_validate_environment(self):
        """Test environment validation function."""
        env_vars = {
            'REDDIT_CLIENT_ID': 'test_id',
            'REDDIT_CLIENT_SECRET': 'test_secret',
            'REDDIT_USER_AGENT': 'TestBot/1.0',
            'ALPHA_VANTAGE_API_KEY': 'test_av_key',
            'GOOGLE_GEMINI_API_KEY': 'test_gemini_key',
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            status = validate_environment()
            
            assert isinstance(status, dict)
            assert 'environment' in status
            assert 'debug' in status
            assert 'database_configured' in status
            assert 'redis_configured' in status
            assert 'external_apis' in status
            assert 'security' in status
            assert 'features' in status
            
            # Check external APIs status
            apis = status['external_apis']
            assert apis['reddit'] is True
            assert apis['alpha_vantage'] is True
            assert apis['gemini'] is True
            
            # Check security status
            security = status['security']
            assert security['secret_key_set'] is True
            assert security['cors_origins_count'] > 0


class TestEnvironmentSpecificSettings:
    """Test environment-specific configuration."""
    
    def test_production_settings(self):
        """Test production-specific settings."""
        env_vars = {
            'REDDIT_CLIENT_ID': 'prod_id',
            'REDDIT_CLIENT_SECRET': 'prod_secret',
            'REDDIT_USER_AGENT': 'ProdBot/1.0',
            'ALPHA_VANTAGE_API_KEY': 'prod_av_key',
            'GOOGLE_GEMINI_API_KEY': 'prod_gemini_key',
            'ENVIRONMENT': 'production',
            'DEBUG': 'false',
            'SECRET_KEY': 'super-secure-production-key-32-chars-long',
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            assert settings.ENVIRONMENT == 'production'
            assert settings.DEBUG is False
            assert settings.is_production is True
            assert len(settings.SECRET_KEY) >= 32
    
    def test_development_settings(self):
        """Test development-specific settings."""
        env_vars = {
            'REDDIT_CLIENT_ID': 'dev_id',
            'REDDIT_CLIENT_SECRET': 'dev_secret',
            'REDDIT_USER_AGENT': 'DevBot/1.0',
            'ALPHA_VANTAGE_API_KEY': 'dev_av_key',
            'GOOGLE_GEMINI_API_KEY': 'dev_gemini_key',
            'ENVIRONMENT': 'development',
            'DEBUG': 'true',
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            assert settings.ENVIRONMENT == 'development'
            assert settings.DEBUG is True
            assert settings.is_development is True
    
    def test_testing_settings(self):
        """Test testing-specific settings."""
        env_vars = {
            'REDDIT_CLIENT_ID': 'test_id',
            'REDDIT_CLIENT_SECRET': 'test_secret',
            'REDDIT_USER_AGENT': 'TestBot/1.0',
            'ALPHA_VANTAGE_API_KEY': 'test_av_key',
            'GOOGLE_GEMINI_API_KEY': 'test_gemini_key',
            'TESTING': 'true',
            'TEST_DATABASE_URL': 'postgresql+asyncpg://test:test@localhost/test_db',
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            assert settings.TESTING is True
            assert settings.is_testing is True
            assert settings.TEST_DATABASE_URL is not None