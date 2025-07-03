#!/usr/bin/env python3
"""
Health Check Script for RottenStocks

This script performs comprehensive health checks on all system components
including Docker services, backend API, database, and Redis.

Usage:
    python scripts/health-check.py
    python scripts/health-check.py --detailed
    python scripts/health-check.py --json
"""

import asyncio
import json
import sys
import time
import argparse
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    import aiohttp
    import asyncpg
    import redis
    import psutil
except ImportError:
    print("Missing dependencies. Install with:")
    print("pip install aiohttp asyncpg redis psutil")
    sys.exit(1)

@dataclass
class HealthStatus:
    """Health status for a service"""
    name: str
    status: str  # "healthy", "unhealthy", "warning"
    message: str
    details: Optional[Dict[str, Any]] = None
    response_time_ms: Optional[float] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

class HealthChecker:
    """Comprehensive health checker for RottenStocks"""
    
    def __init__(self, detailed: bool = False):
        self.detailed = detailed
        self.results: List[HealthStatus] = []
    
    async def check_all(self) -> List[HealthStatus]:
        """Run all health checks"""
        print("🏥 Running RottenStocks Health Check...")
        print("=" * 50)
        
        # Run all checks concurrently where possible
        checks = [
            self.check_docker_services(),
            self.check_database(),
            self.check_redis(),
            self.check_backend_api(),
            self.check_system_resources(),
        ]
        
        # Frontend check (if running)
        try:
            checks.append(self.check_frontend())
        except:
            pass
        
        await asyncio.gather(*checks, return_exceptions=True)
        
        return self.results
    
    async def check_docker_services(self) -> None:
        """Check Docker services status"""
        start_time = time.time()
        
        try:
            # Check if Docker is running
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self.results.append(HealthStatus(
                    name="Docker",
                    status="unhealthy",
                    message="Docker is not running or not accessible",
                    response_time_ms=(time.time() - start_time) * 1000
                ))
                return
            
            # Check docker-compose services
            result = subprocess.run(
                ["docker-compose", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                services = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            service = json.loads(line)
                            services.append({
                                "name": service.get("Service", "unknown"),
                                "state": service.get("State", "unknown"),
                                "health": service.get("Health", "unknown")
                            })
                        except json.JSONDecodeError:
                            continue
                
                healthy_services = [s for s in services if s["state"] in ["running", "Up"]]
                
                if len(healthy_services) == len(services) and len(services) > 0:
                    status = "healthy"
                    message = f"All {len(services)} Docker services running"
                elif len(healthy_services) > 0:
                    status = "warning"
                    message = f"{len(healthy_services)}/{len(services)} Docker services running"
                else:
                    status = "unhealthy"
                    message = "No Docker services running"
                
                self.results.append(HealthStatus(
                    name="Docker Services",
                    status=status,
                    message=message,
                    details={"services": services} if self.detailed else None,
                    response_time_ms=(time.time() - start_time) * 1000
                ))
            else:
                self.results.append(HealthStatus(
                    name="Docker Services",
                    status="warning",
                    message="No docker-compose services found or not running",
                    response_time_ms=(time.time() - start_time) * 1000
                ))
        
        except subprocess.TimeoutExpired:
            self.results.append(HealthStatus(
                name="Docker Services",
                status="unhealthy",
                message="Docker command timed out",
                response_time_ms=(time.time() - start_time) * 1000
            ))
        except Exception as e:
            self.results.append(HealthStatus(
                name="Docker Services",
                status="unhealthy",
                message=f"Docker check failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000
            ))
    
    async def check_database(self) -> None:
        """Check PostgreSQL database connectivity"""
        start_time = time.time()
        
        try:
            # Try to connect to the database
            conn = await asyncpg.connect(
                host="localhost",
                port=5432,
                user="postgres",
                password="postgres",
                database="rottenstocks",
                timeout=10
            )
            
            # Test basic query
            version = await conn.fetchval("SELECT version();")
            await conn.close()
            
            postgres_version = version.split()[1] if version else "unknown"
            
            self.results.append(HealthStatus(
                name="PostgreSQL Database",
                status="healthy",
                message="Database connection successful",
                details={"version": postgres_version} if self.detailed else None,
                response_time_ms=(time.time() - start_time) * 1000
            ))
        
        except asyncio.TimeoutError:
            self.results.append(HealthStatus(
                name="PostgreSQL Database",
                status="unhealthy",
                message="Database connection timed out",
                response_time_ms=(time.time() - start_time) * 1000
            ))
        except Exception as e:
            self.results.append(HealthStatus(
                name="PostgreSQL Database",
                status="unhealthy",
                message=f"Database connection failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000
            ))
    
    async def check_redis(self) -> None:
        """Check Redis connectivity"""
        start_time = time.time()
        
        try:
            # Connect to Redis
            r = redis.Redis(host="localhost", port=6379, decode_responses=True, socket_timeout=10)
            
            # Test basic operations
            ping_result = r.ping()
            info = r.info() if self.detailed else {}
            
            if ping_result:
                self.results.append(HealthStatus(
                    name="Redis Cache",
                    status="healthy",
                    message="Redis connection successful",
                    details={
                        "version": info.get("redis_version", "unknown"),
                        "memory_usage": info.get("used_memory_human", "unknown")
                    } if self.detailed else None,
                    response_time_ms=(time.time() - start_time) * 1000
                ))
            else:
                self.results.append(HealthStatus(
                    name="Redis Cache",
                    status="unhealthy",
                    message="Redis ping failed",
                    response_time_ms=(time.time() - start_time) * 1000
                ))
        
        except redis.TimeoutError:
            self.results.append(HealthStatus(
                name="Redis Cache",
                status="unhealthy",
                message="Redis connection timed out",
                response_time_ms=(time.time() - start_time) * 1000
            ))
        except Exception as e:
            self.results.append(HealthStatus(
                name="Redis Cache",
                status="unhealthy",
                message=f"Redis connection failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000
            ))
    
    async def check_backend_api(self) -> None:
        """Check backend API health"""
        start_time = time.time()
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Check health endpoint
                async with session.get("http://localhost:8000/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        self.results.append(HealthStatus(
                            name="Backend API",
                            status="healthy",
                            message="API health check successful",
                            details=data if self.detailed else None,
                            response_time_ms=(time.time() - start_time) * 1000
                        ))
                    else:
                        self.results.append(HealthStatus(
                            name="Backend API",
                            status="unhealthy",
                            message=f"API health check failed with status {response.status}",
                            response_time_ms=(time.time() - start_time) * 1000
                        ))
        
        except asyncio.TimeoutError:
            self.results.append(HealthStatus(
                name="Backend API",
                status="unhealthy",
                message="API health check timed out",
                response_time_ms=(time.time() - start_time) * 1000
            ))
        except aiohttp.ClientConnectorError:
            self.results.append(HealthStatus(
                name="Backend API",
                status="unhealthy",
                message="Cannot connect to API (server not running?)",
                response_time_ms=(time.time() - start_time) * 1000
            ))
        except Exception as e:
            self.results.append(HealthStatus(
                name="Backend API",
                status="unhealthy",
                message=f"API health check failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000
            ))
    
    async def check_frontend(self) -> None:
        """Check frontend availability"""
        start_time = time.time()
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get("http://localhost:5173") as response:
                    if response.status == 200:
                        self.results.append(HealthStatus(
                            name="Frontend",
                            status="healthy",
                            message="Frontend is accessible",
                            response_time_ms=(time.time() - start_time) * 1000
                        ))
                    else:
                        self.results.append(HealthStatus(
                            name="Frontend",
                            status="warning",
                            message=f"Frontend returned status {response.status}",
                            response_time_ms=(time.time() - start_time) * 1000
                        ))
        
        except aiohttp.ClientConnectorError:
            self.results.append(HealthStatus(
                name="Frontend",
                status="warning",
                message="Frontend not accessible (dev server not running?)",
                response_time_ms=(time.time() - start_time) * 1000
            ))
        except Exception as e:
            self.results.append(HealthStatus(
                name="Frontend",
                status="warning",
                message=f"Frontend check failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000
            ))
    
    async def check_system_resources(self) -> None:
        """Check system resources"""
        start_time = time.time()
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Determine status based on resource usage
            status = "healthy"
            issues = []
            
            if cpu_percent > 90:
                status = "warning"
                issues.append(f"High CPU usage: {cpu_percent}%")
            
            if memory.percent > 90:
                status = "warning"
                issues.append(f"High memory usage: {memory.percent}%")
            
            if disk.percent > 90:
                status = "warning"
                issues.append(f"High disk usage: {disk.percent}%")
            
            message = "System resources normal"
            if issues:
                message = f"Resource warnings: {', '.join(issues)}"
            
            self.results.append(HealthStatus(
                name="System Resources",
                status=status,
                message=message,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                    "disk_percent": disk.percent,
                    "disk_free_gb": round(disk.free / (1024**3), 2)
                } if self.detailed else None,
                response_time_ms=(time.time() - start_time) * 1000
            ))
        
        except Exception as e:
            self.results.append(HealthStatus(
                name="System Resources",
                status="warning",
                message=f"System resource check failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000
            ))

def print_results(results: List[HealthStatus], json_output: bool = False) -> None:
    """Print health check results"""
    if json_output:
        output = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": get_overall_status(results),
            "services": [asdict(result) for result in results]
        }
        print(json.dumps(output, indent=2))
        return
    
    # Console output
    print("\n📊 Health Check Results")
    print("=" * 50)
    
    for result in results:
        status_emoji = {
            "healthy": "✅",
            "warning": "⚠️",
            "unhealthy": "❌"
        }.get(result.status, "❓")
        
        response_time = f" ({result.response_time_ms:.1f}ms)" if result.response_time_ms else ""
        print(f"{status_emoji} {result.name}: {result.message}{response_time}")
        
        if result.details:
            for key, value in result.details.items():
                print(f"   └─ {key}: {value}")
    
    # Overall status
    overall = get_overall_status(results)
    overall_emoji = {
        "healthy": "🟢",
        "warning": "🟡", 
        "unhealthy": "🔴"
    }.get(overall, "❓")
    
    print(f"\n{overall_emoji} Overall Status: {overall.upper()}")
    
    # Summary
    healthy = len([r for r in results if r.status == "healthy"])
    warning = len([r for r in results if r.status == "warning"])
    unhealthy = len([r for r in results if r.status == "unhealthy"])
    
    print(f"📈 Summary: {healthy} healthy, {warning} warnings, {unhealthy} unhealthy")

def get_overall_status(results: List[HealthStatus]) -> str:
    """Determine overall system status"""
    if any(r.status == "unhealthy" for r in results):
        return "unhealthy"
    elif any(r.status == "warning" for r in results):
        return "warning"
    else:
        return "healthy"

async def main():
    parser = argparse.ArgumentParser(description="RottenStocks Health Check")
    parser.add_argument("--detailed", action="store_true", help="Include detailed information")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    
    args = parser.parse_args()
    
    checker = HealthChecker(detailed=args.detailed)
    results = await checker.check_all()
    
    print_results(results, args.json)
    
    # Exit with appropriate code
    overall_status = get_overall_status(results)
    if overall_status == "unhealthy":
        sys.exit(1)
    elif overall_status == "warning":
        sys.exit(2)
    else:
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())