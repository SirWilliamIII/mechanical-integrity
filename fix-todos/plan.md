# TODO Resolution Plan - Mechanical Integrity Safety-Critical System

**Session Started**: 2024-08-23  
**Total TODOs Found**: 31  
**Safety Priority**: CRITICAL - Petroleum industry compliance system

## Priority Classification

### 🚨 **CRITICAL - SAFETY & PRODUCTION** (Priority 1)
These affect production readiness and safety compliance:

1. **[PRODUCTION] Set development defaults to production-safe values** - `backend/core/config.py:20`
   - **Risk**: HIGH - Development settings in production
   - **Action**: Remove DEBUG=True defaults, require explicit config
   
2. **[SERVICES] Implement Redis and Ollama health checks for production readiness** - `backend/app/main.py:61`
   - **Risk**: HIGH - Missing service monitoring
   - **Action**: Add health endpoints for background services

3. **[SCHEMA] Update expected table list for complete database schema** - `backend/app/services/health/checks.py:191`
   - **Risk**: MEDIUM - Incomplete health validation
   - **Action**: Check all required tables in health endpoint

4. **[SECURITY] Add input sanitization for extracted equipment tags** - `backend/app/services/document_analyzer.py:176`
   - **Risk**: HIGH - Security vulnerability
   - **Action**: Sanitize extracted data from documents

### ⚠️ **HIGH - SYSTEM STABILITY** (Priority 2)
Issues affecting core functionality:

5. **[BACKGROUND_TASKS] Fix session isolation issues for background calculations** - `backend/app/services/api579_service.py:52`
   - **Risk**: HIGH - Data corruption risk
   - **Action**: Fix database session management

6. **[INTEGRATION_TESTS] Add missing API routers causing 404 errors in tests** - `backend/app/main.py:15`
   - **Risk**: MEDIUM - Missing endpoints
   - **Action**: Add missing calculation routers

7. **[DEPRECATION] Replace deprecated close() with aclose()** - `backend/app/services/health/checks.py:80`
   - **Risk**: MEDIUM - Future compatibility
   - **Action**: Update Redis client usage

8. **[TEST_FAILURE] Fix hardcoded confidence level** - `backend/app/api/inspections.py:436`
   - **Risk**: MEDIUM - Test failures
   - **Action**: Implement dynamic confidence calculation

### 🔧 **MEDIUM - TECHNICAL DEBT** (Priority 3)
Deprecations and improvements:

9. **[DEPRECATION] Migrate Pydantic v1 @validator to v2 @field_validator** - `backend/app/api/equipment.py:40`
   - **Risk**: LOW - Deprecation warnings
   - **Action**: Update to Pydantic v2 syntax

10. **[DEPRECATION] Replace deprecated json_encoders with Pydantic v2 serializers** - `backend/app/api/equipment.py:54`
    - **Risk**: LOW - Deprecation warnings
    - **Action**: Update serialization approach

11. **[DATABASE] Remove hardcoded default confidence level from model** - `backend/models/inspection.py:121`
    - **Risk**: LOW - Hard-coded values
    - **Action**: Make confidence level calculated

12. **[TESTING] Replace mock get_db() with proper test database fixture** - `backend/tests/conftest.py:33`
    - **Risk**: LOW - Test quality
    - **Action**: Implement proper test database

### 🎯 **ENHANCEMENT - FEATURES** (Priority 4)
Nice-to-have improvements:

13. **[VALIDATION] Add comprehensive material-pressure-temperature validation** - `backend/app/api/equipment.py:51`
14. **[FEATURE] Implement risk-based inspection interval calculation** - `backend/app/api/equipment.py:366`
15. **[VALIDATION] Implement thickness measurement validation against API 579 limits** - `backend/app/services/document_analyzer.py:57`
16. **[PERFORMANCE] Implement pressure validation caching** - `backend/app/validation/validators.py:280`
17. **[FEATURE] Add statistical analysis for corrosion rate validation** - `backend/app/validation/validators.py:469`
18. **[MONITORING] Add request metrics collection for APM integration** - `backend/app/main.py:126`

### 📊 **LOW PRIORITY - ADVANCED FEATURES** (Priority 5)
Future enhancements:

19. **[FEATURE] Add OCR capability for scanned inspection reports** - `backend/app/services/document_analyzer.py:55`
20. **[ENHANCEMENT] Add fallback extraction methods for critical data** - `backend/app/services/document_analyzer.py:96`
21. **[DATA] Expand material database with additional ASME materials** - `backend/app/calculations/constants.py:164`
22. **[FEATURE] Add Level 2 and Level 3 assessment criteria** - `backend/app/calculations/constants.py:289`
23. **[FEATURE] Auto-switch to thick-wall calculations when t/R > 0.1** - `backend/app/calculations/dual_path_calculator.py:172`
24. **[ENHANCEMENT] Add Monte Carlo simulation for remaining life uncertainty** - `backend/app/calculations/dual_path_calculator.py:411`
25. **Frontend: Implement draft saving functionality** - `frontend/src/components/forms/InspectionForm.vue:528`

## Implementation Strategy

### Phase 1: Critical Safety Issues (Priority 1)
Focus on production readiness and security:
1. Fix production configuration defaults
2. Implement service health checks
3. Add security sanitization
4. Complete database schema validation

### Phase 2: System Stability (Priority 2)
Resolve core functionality issues:
1. Fix background task session isolation
2. Add missing API endpoints
3. Update deprecated Redis client calls
4. Fix confidence level calculation

### Phase 3: Technical Debt (Priority 3)
Clean up deprecations and improve code quality:
1. Migrate to Pydantic v2
2. Improve test infrastructure
3. Remove hard-coded values

## Session State Tracking

**Current Status**: PHASE 1 COMPLETED ✅  
**Next TODO**: #6 - Missing API routers (Priority 2)  
**Completed**: 5/31 (16% complete)  
**In Progress**: Analysis of remaining test failures  

### Completed TODOs (Phase 1: Critical Safety Issues)

✅ **TODO #1**: Production configuration defaults - Fixed DEBUG and ENVIRONMENT defaults with safety validation  
✅ **TODO #2**: Redis and Ollama health checks - Implemented comprehensive service monitoring  
✅ **TODO #3**: Database schema validation - Updated to check all 4 required tables  
✅ **TODO #4**: Input sanitization - Added comprehensive security validation for equipment tags  
✅ **TODO #5**: Session isolation for background calculations - Implemented session-per-task pattern

### Current Test Status
- **108 tests passing** (+8 improvement)
- **15 tests failing** (down from session isolation issues)
- **Session isolation fix successful** - Core API579Service working correctly
- **Production safety implemented** - All critical safety TODOs resolved  