# TODO TECH DEBT

This document tracks technical debt and maintenance tasks that need to be addressed in the RottenStocks project.

## High Priority Issues

### 🧪 Testing Infrastructure

#### [ ] Run all root tests and fix them
**Priority:** High  
**Estimated Effort:** 2-4 hours  
**Description:** The backend test suite is currently showing 5 failed tests out of 182 total tests. While all database model tests (74/74) are passing successfully, there are failures in:

**Specific Failing Tests (as of 2025-07-04):**
1. `tests/test_main.py::test_cors_headers` - CORS preflight returning 400 instead of 200/204
2. `tests/test_middleware.py::TestCORSMiddleware::test_cors_preflight_request` - CORS preflight configuration issue
3. `tests/test_middleware.py::TestCORSMiddleware::test_cors_simple_request` - CORS simple request functionality
4. `tests/test_middleware.py::TestErrorHandlingMiddleware::test_500_error_handling` - Error handling middleware
5. `tests/test_middleware.py::TestMiddlewareIntegration::test_all_middleware_headers_present` - Middleware integration issue

**Impact:** These test failures prevent reliable CI/CD deployment and could hide integration issues.

#### [ ] Fix remaining external API tests
**Priority:** Medium  
**Estimated Effort:** 1-2 hours  
**Description:** External APIs module has 91% test pass rate (52/57 tests passing). 5 tests remain failing after major fixes.

**Specific Failing Tests (as of 2025-07-04):**
1. `tests/external_apis/test_alpha_vantage_client.py::TestAlphaVantageClient::test_get_quote_invalid_format` - Client expecting exception, now gets error response
2. `tests/external_apis/test_alpha_vantage_client.py::TestAlphaVantageClient::test_get_quote_empty_data` - Client expecting exception, now gets error response  
3. `tests/external_apis/test_alpha_vantage_integration.py::test_get_daily_time_series_integration` - API response format changed (missing "4. Time Zone")
4. `tests/external_apis/test_alpha_vantage_integration.py::test_service_get_overview_integration` - Service-level test issue
5. `tests/external_apis/test_alpha_vantage_integration.py::test_service_caching_integration` - Caching functionality test issue

**Impact:** These test failures don't block core functionality but affect confidence in external API integrations.

**Notes:** Major improvements already implemented - fixed rate limiter tests, base client tests, and most Alpha Vantage integration tests. Remaining failures are edge cases and API format changes.

**Files Affected:**
- `tests/test_config.py` - Environment and CORS configuration tests
- `tests/test_health_endpoints.py` - Health check endpoint tests
- `tests/test_main.py` - Main application tests
- `tests/test_middleware.py` - Middleware functionality tests  
- `tests/test_security.py` - JWT and security tests
- `tests/test_dependencies.py` - Dependency injection tests

**Root Causes:**
1. AsyncClient initialization issues in test setup
2. JWT token expiry time delta calculation problems
3. CORS middleware configuration mismatches
4. Missing correlation ID and request logger dependencies
5. Health endpoint response format inconsistencies

**Acceptance Criteria:**
- [ ] All 182 backend tests pass successfully
- [ ] Test coverage remains above 80% (currently at 40.38%)
- [ ] No test warnings or errors in output
- [ ] CI/CD pipeline can run tests reliably
- [ ] All async test patterns working correctly

**Related Issues:**
- Test coverage currently at 40.38% (below 80% requirement)
- Some untested utility scripts (migration_utils.py, seed_data.py)
- Repository pattern implementations need test coverage

---

## Medium Priority Issues

### 📝 Documentation
- [ ] Add API documentation generation from OpenAPI spec
- [ ] Create deployment guide for production environments
- [ ] Document database migration best practices

### 🔧 Code Quality  
- [x] ~~Fix deprecated `datetime.utcnow()` warnings in models~~ (Completed 2025-07-04)
- [ ] Standardize error handling patterns across endpoints
- [ ] Add type hints to remaining utility functions

### 🚀 Performance
- [ ] Add database query performance monitoring
- [ ] Implement connection pooling optimization
- [ ] Add caching layer for frequently accessed data

---

## Low Priority Issues

### 🧹 Cleanup
- [ ] Remove unused imports in test files
- [ ] Standardize naming conventions across modules
- [ ] Consolidate duplicate utility functions

---

## Completed Items

✅ **Database Models Testing** - All 74 database model tests passing (100% coverage)  
✅ **Migration System** - Database migrations working with rollback capability  
✅ **Manual Model Testing** - All CRUD operations and relationships verified  
✅ **Database Improvement Plan** - Implemented comprehensive database utilities, repositories, and configuration (2025-07-04)
✅ **DateTime Timezone Fixes** - Fixed all datetime.utcnow() deprecation warnings (2025-07-04)  

---

## Notes

- Focus on fixing the test infrastructure first as it blocks other development
- Database layer is solid and ready for API development
- Consider adding automated test result reporting to track progress