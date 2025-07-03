#!/usr/bin/env python3
"""
Environment Variables Validator for RottenStocks

This script validates that all required environment variables are set
and have appropriate values for the current environment.

Usage:
    python scripts/env-validator.py
    python scripts/env-validator.py --env production
    python scripts/env-validator.py --check-optional
"""

import os
import sys
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse

class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_colored(text: str, color: str = Colors.WHITE) -> None:
    """Print colored text to terminal"""
    print(f"{color}{text}{Colors.END}")

def print_header(text: str) -> None:
    """Print section header"""
    print_colored(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print_colored(f"{Colors.BOLD}{text.center(60)}{Colors.END}")
    print_colored(f"{Colors.BOLD}{'='*60}{Colors.END}")

class EnvValidator:
    """Environment variables validator"""
    
    def __init__(self, env_type: str = "development"):
        self.env_type = env_type
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.success: List[str] = []
        
        # Load environment file if it exists
        self._load_env_file()
    
    def _load_env_file(self) -> None:
        """Load environment variables from .env file"""
        env_files = {
            'development': '.env',
            'test': '.env.test',
            'production': None  # Production uses system environment
        }
        
        env_file = env_files.get(self.env_type)
        if env_file and Path(env_file).exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
                print_colored(f"Loaded environment from {env_file}", Colors.BLUE)
            except ImportError:
                print_colored("Warning: python-dotenv not installed. Install with: pip install python-dotenv", Colors.YELLOW)
    
    def validate_required_vars(self) -> None:
        """Validate all required environment variables"""
        print_header("REQUIRED ENVIRONMENT VARIABLES")
        
        required_vars = self._get_required_vars()
        
        for var_name, validator in required_vars.items():
            value = os.getenv(var_name)
            
            if value is None:
                self.errors.append(f"Missing required variable: {var_name}")
                print_colored(f"✗ {var_name}: MISSING", Colors.RED)
                continue
            
            # Run custom validator if provided
            if validator and not validator(value):
                self.errors.append(f"Invalid value for {var_name}")
                print_colored(f"✗ {var_name}: INVALID VALUE", Colors.RED)
                continue
            
            self.success.append(f"{var_name}: OK")
            print_colored(f"✓ {var_name}: OK", Colors.GREEN)
    
    def validate_optional_vars(self) -> None:
        """Validate optional environment variables"""
        print_header("OPTIONAL ENVIRONMENT VARIABLES")
        
        optional_vars = self._get_optional_vars()
        
        for var_name, validator in optional_vars.items():
            value = os.getenv(var_name)
            
            if value is None:
                print_colored(f"○ {var_name}: NOT SET (using default)", Colors.YELLOW)
                continue
            
            if validator and not validator(value):
                self.warnings.append(f"Invalid value for optional variable: {var_name}")
                print_colored(f"! {var_name}: INVALID VALUE", Colors.YELLOW)
                continue
            
            print_colored(f"✓ {var_name}: OK", Colors.GREEN)
    
    def validate_environment_specific(self) -> None:
        """Validate environment-specific requirements"""
        print_header(f"ENVIRONMENT-SPECIFIC VALIDATION ({self.env_type.upper()})")
        
        if self.env_type == "production":
            self._validate_production()
        elif self.env_type == "development":
            self._validate_development()
        elif self.env_type == "test":
            self._validate_test()
    
    def _validate_production(self) -> None:
        """Production-specific validations"""
        # Check that debug is disabled
        debug = os.getenv('DEBUG', '').lower()
        if debug in ('true', '1', 'yes'):
            self.errors.append("DEBUG should be false in production")
            print_colored("✗ DEBUG: Should be false in production", Colors.RED)
        else:
            print_colored("✓ DEBUG: Correctly disabled", Colors.GREEN)
        
        # Check JWT secret strength
        jwt_secret = os.getenv('JWT_SECRET_KEY', '')
        if len(jwt_secret) < 32:
            self.errors.append("JWT_SECRET_KEY too short for production (minimum 32 characters)")
            print_colored("✗ JWT_SECRET_KEY: Too short for production", Colors.RED)
        else:
            print_colored("✓ JWT_SECRET_KEY: Adequate length", Colors.GREEN)
        
        # Check database URL is not localhost
        db_url = os.getenv('DATABASE_URL', '')
        if 'localhost' in db_url or '127.0.0.1' in db_url:
            self.warnings.append("DATABASE_URL points to localhost in production")
            print_colored("! DATABASE_URL: Points to localhost", Colors.YELLOW)
        else:
            print_colored("✓ DATABASE_URL: Not localhost", Colors.GREEN)
    
    def _validate_development(self) -> None:
        """Development-specific validations"""
        # Check that required dev services are configured
        services = {
            'DATABASE_URL': 'PostgreSQL',
            'REDIS_URL': 'Redis'
        }
        
        for var, service in services.items():
            value = os.getenv(var, '')
            if 'localhost' in value or '127.0.0.1' in value:
                print_colored(f"✓ {service}: Configured for localhost", Colors.GREEN)
            else:
                self.warnings.append(f"{service} not configured for localhost")
                print_colored(f"! {service}: Not localhost (may need Docker)", Colors.YELLOW)
    
    def _validate_test(self) -> None:
        """Test-specific validations"""
        # Check test database is separate
        db_url = os.getenv('DATABASE_URL', '')
        if 'test' not in db_url.lower():
            self.warnings.append("Test DATABASE_URL should contain 'test'")
            print_colored("! DATABASE_URL: Should contain 'test'", Colors.YELLOW)
        else:
            print_colored("✓ DATABASE_URL: Contains 'test'", Colors.GREEN)
        
        # Check Redis test DB
        redis_url = os.getenv('REDIS_URL', '')
        if not redis_url.endswith(('/15', '/14', '/13')):
            self.warnings.append("Test REDIS_URL should use a high-numbered database")
            print_colored("! REDIS_URL: Should use test database number", Colors.YELLOW)
        else:
            print_colored("✓ REDIS_URL: Using test database", Colors.GREEN)
    
    def _get_required_vars(self) -> Dict[str, Optional[callable]]:
        """Get required environment variables with validators"""
        base_required = {
            'REDDIT_CLIENT_ID': self._validate_non_empty,
            'REDDIT_CLIENT_SECRET': self._validate_non_empty,
            'REDDIT_USER_AGENT': self._validate_user_agent,
            'ALPHA_VANTAGE_API_KEY': self._validate_non_empty,
            'GOOGLE_GEMINI_API_KEY': self._validate_non_empty,
            'DATABASE_URL': self._validate_database_url,
            'REDIS_URL': self._validate_redis_url,
            'JWT_SECRET_KEY': self._validate_jwt_secret,
        }
        
        if self.env_type == "production":
            base_required.update({
                'ENVIRONMENT': lambda x: x == 'production',
                'DEBUG': lambda x: x.lower() in ('false', '0', 'no'),
            })
        
        return base_required
    
    def _get_optional_vars(self) -> Dict[str, Optional[callable]]:
        """Get optional environment variables with validators"""
        return {
            'API_V1_PREFIX': self._validate_api_prefix,
            'HOST': self._validate_host,
            'PORT': self._validate_port,
            'LOG_LEVEL': self._validate_log_level,
            'WORKERS': self._validate_positive_int,
            'DB_POOL_SIZE': self._validate_positive_int,
            'RATE_LIMIT_PER_MINUTE': self._validate_positive_int,
            'ALLOWED_ORIGINS': self._validate_origins,
        }
    
    # Validator functions
    def _validate_non_empty(self, value: str) -> bool:
        """Validate that value is not empty"""
        return bool(value and value.strip())
    
    def _validate_user_agent(self, value: str) -> bool:
        """Validate Reddit user agent format"""
        pattern = r'^[A-Za-z0-9_-]+/\d+\.\d+(\.\d+)?\s+by\s+[A-Za-z0-9_-]+$'
        return bool(re.match(pattern, value))
    
    def _validate_database_url(self, value: str) -> bool:
        """Validate database URL format"""
        try:
            parsed = urlparse(value)
            return parsed.scheme == 'postgresql' and parsed.hostname and parsed.path
        except:
            return False
    
    def _validate_redis_url(self, value: str) -> bool:
        """Validate Redis URL format"""
        try:
            parsed = urlparse(value)
            return parsed.scheme == 'redis' and parsed.hostname
        except:
            return False
    
    def _validate_jwt_secret(self, value: str) -> bool:
        """Validate JWT secret strength"""
        if self.env_type == "production":
            return len(value) >= 32 and not value.startswith('your-')
        return len(value) >= 16
    
    def _validate_api_prefix(self, value: str) -> bool:
        """Validate API prefix format"""
        return value.startswith('/') and len(value) > 1
    
    def _validate_host(self, value: str) -> bool:
        """Validate host format"""
        return value in ('0.0.0.0', '127.0.0.1', 'localhost') or self._validate_ip(value)
    
    def _validate_port(self, value: str) -> bool:
        """Validate port number"""
        try:
            port = int(value)
            return 1 <= port <= 65535
        except ValueError:
            return False
    
    def _validate_log_level(self, value: str) -> bool:
        """Validate log level"""
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        return value.upper() in valid_levels
    
    def _validate_positive_int(self, value: str) -> bool:
        """Validate positive integer"""
        try:
            return int(value) > 0
        except ValueError:
            return False
    
    def _validate_origins(self, value: str) -> bool:
        """Validate CORS origins"""
        origins = [origin.strip() for origin in value.split(',')]
        for origin in origins:
            try:
                parsed = urlparse(origin)
                if not parsed.scheme or not parsed.hostname:
                    return False
            except:
                return False
        return True
    
    def _validate_ip(self, value: str) -> bool:
        """Validate IP address"""
        try:
            import ipaddress
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False
    
    def print_summary(self) -> None:
        """Print validation summary"""
        print_header("VALIDATION SUMMARY")
        
        if self.success:
            print_colored(f"✓ {len(self.success)} variables validated successfully", Colors.GREEN)
        
        if self.warnings:
            print_colored(f"! {len(self.warnings)} warnings:", Colors.YELLOW)
            for warning in self.warnings:
                print_colored(f"  - {warning}", Colors.YELLOW)
        
        if self.errors:
            print_colored(f"✗ {len(self.errors)} errors found:", Colors.RED)
            for error in self.errors:
                print_colored(f"  - {error}", Colors.RED)
        
        if not self.errors and not self.warnings:
            print_colored("🎉 All environment variables are properly configured!", Colors.GREEN)
        elif not self.errors:
            print_colored("✓ No critical errors found. Warnings should be reviewed.", Colors.GREEN)
        else:
            print_colored("❌ Critical errors found. Please fix before running the application.", Colors.RED)
    
    def get_exit_code(self) -> int:
        """Return appropriate exit code"""
        return 1 if self.errors else 0

def main():
    parser = argparse.ArgumentParser(description="Validate RottenStocks environment variables")
    parser.add_argument(
        '--env', 
        choices=['development', 'test', 'production'],
        default='development',
        help='Environment type to validate for'
    )
    parser.add_argument(
        '--check-optional',
        action='store_true',
        help='Also validate optional environment variables'
    )
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output'
    )
    
    args = parser.parse_args()
    
    # Disable colors if requested
    if args.no_color:
        for attr in dir(Colors):
            if not attr.startswith('_'):
                setattr(Colors, attr, '')
    
    print_colored(f"{Colors.BOLD}RottenStocks Environment Validator{Colors.END}", Colors.CYAN)
    print_colored(f"Environment: {args.env}", Colors.BLUE)
    
    validator = EnvValidator(args.env)
    
    # Run validations
    validator.validate_required_vars()
    
    if args.check_optional:
        validator.validate_optional_vars()
    
    validator.validate_environment_specific()
    validator.print_summary()
    
    sys.exit(validator.get_exit_code())

if __name__ == "__main__":
    main()