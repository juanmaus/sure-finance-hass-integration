# API Integration Validation Tests

This document provides comprehensive manual test cases to validate the Sure Finance API integration functionality, including authentication, data retrieval, and error handling scenarios.

## Test Overview

The Sure Finance integration connects to a financial API to retrieve account balances, transactions, and calculate financial metrics. These tests ensure robust API integration with proper error handling and data validation.

## Test Environment Setup

### Prerequisites
- Local Home Assistant development environment
- Valid Sure Finance API credentials
- Network connectivity to Sure Finance API
- Debug logging enabled

### Test Data Requirements
- Test API key with appropriate permissions
- Sure Finance account with sample financial data
- Multiple account types (checking, savings, credit, etc.)
- Historical transaction data
- Various transaction categories

## Authentication Tests

### Test Case: AUTH-001 - Valid API Key Authentication
**Objective**: Verify successful authentication with valid API key

**Pre-conditions**:
- Valid API key available
- Network connectivity to API endpoint

**Test Steps**:
1. Configure integration with valid API key
2. Start Home Assistant
3. Monitor logs for authentication success
4. Verify integration loads without errors

**Expected Results**:
- ✅ Integration authenticates successfully
- ✅ No authentication errors in logs
- ✅ API client establishes connection
- ✅ Integration status shows "Loaded"

**Validation Commands**:
```bash
# Check authentication in logs
grep -i "auth" /config/home-assistant.log | grep sure_finance

# Verify integration status
grep "sure_finance.*setup" /config/home-assistant.log
```

### Test Case: AUTH-002 - Invalid API Key Handling
**Objective**: Verify proper handling of invalid API key

**Pre-conditions**:
- Invalid or expired API key

**Test Steps**:
1. Configure integration with invalid API key
2. Attempt to add integration
3. Observe error handling behavior
4. Check error message clarity

**Expected Results**:
- ❌ Integration setup fails gracefully
- ✅ Clear error message displayed to user
- ✅ No sensitive information exposed in logs
- ✅ Integration can be reconfigured

### Test Case: AUTH-003 - API Key Permission Validation
**Objective**: Verify handling of API key with insufficient permissions

**Pre-conditions**:
- API key with limited permissions

**Test Steps**:
1. Use API key with read-only permissions
2. Configure integration
3. Monitor API calls and responses
4. Verify graceful degradation

**Expected Results**:
- ✅ Integration handles permission errors gracefully
- ✅ Appropriate error messages displayed
- ✅ No application crashes

## Data Retrieval Tests

### Test Case: DATA-001 - Account Data Retrieval
**Objective**: Verify successful retrieval of account information

**Pre-conditions**:
- Valid authentication established
- Multiple accounts in Sure Finance

**Test Steps**:
1. Trigger account data refresh
2. Monitor API calls in logs
3. Verify account entities creation
4. Check account balance accuracy

**Expected Results**:
- ✅ All accounts retrieved successfully
- ✅ Account balances match Sure Finance UI
- ✅ Account entities created with correct attributes
- ✅ Account names and types properly mapped

**Validation Commands**:
```bash
# Check account retrieval
grep "get_accounts" /config/home-assistant.log

# Verify entity creation
grep "sensor.sure_finance_account" /config/home-assistant.log
```

### Test Case: DATA-002 - Transaction Data Retrieval
**Objective**: Verify successful retrieval of transaction data

**Pre-conditions**:
- Valid authentication
- Historical transaction data available

**Test Steps**:
1. Configure date range for transaction retrieval
2. Trigger data refresh
3. Monitor transaction API calls
4. Verify transaction data accuracy

**Expected Results**:
- ✅ Transactions retrieved within specified date range
- ✅ Transaction amounts and categories correct
- ✅ Pagination handled properly for large datasets
- ✅ Transaction data used in financial calculations

### Test Case: DATA-003 - Financial Metrics Calculation
**Objective**: Verify accurate calculation of financial metrics

**Pre-conditions**:
- Account and transaction data available
- Known expected values for verification

**Test Steps**:
1. Retrieve current financial data
2. Calculate expected values manually
3. Compare with integration calculations
4. Verify sensor state accuracy

**Expected Results**:
- ✅ Net worth calculation accurate
- ✅ Cashflow calculations correct
- ✅ Outflow calculations accurate
- ✅ Savings rate calculation proper
- ✅ Liability calculations correct

**Manual Verification**:
```python
# Example verification script
def verify_net_worth(accounts):
    assets = sum(acc.balance for acc in accounts if acc.type in ['checking', 'savings'])
    liabilities = sum(acc.balance for acc in accounts if acc.type == 'credit')
    return assets - liabilities
```

## Error Handling Tests

### Test Case: ERROR-001 - Network Connectivity Issues
**Objective**: Verify graceful handling of network connectivity problems

**Pre-conditions**:
- Integration configured and working
- Ability to simulate network issues

**Test Steps**:
1. Establish normal operation
2. Simulate network disconnection
3. Observe integration behavior
4. Restore connectivity and verify recovery

**Expected Results**:
- ✅ Integration handles network errors gracefully
- ✅ Cached data used during outages
- ✅ Automatic retry mechanism functions
- ✅ Recovery occurs when connectivity restored

### Test Case: ERROR-002 - API Rate Limiting
**Objective**: Verify proper handling of API rate limits

**Pre-conditions**:
- Integration configured with aggressive refresh rates
- API rate limits known

**Test Steps**:
1. Configure short update intervals
2. Monitor API call frequency
3. Trigger rate limit responses
4. Observe backoff behavior

**Expected Results**:
- ✅ Rate limit errors detected and handled
- ✅ Exponential backoff implemented
- ✅ No excessive API calls during rate limiting
- ✅ Normal operation resumes after backoff

### Test Case: ERROR-003 - Malformed API Responses
**Objective**: Verify handling of unexpected API response formats

**Pre-conditions**:
- Ability to mock API responses
- Various malformed response scenarios

**Test Steps**:
1. Mock API to return malformed JSON
2. Mock API to return unexpected data structures
3. Mock API to return partial data
4. Observe integration error handling

**Expected Results**:
- ✅ JSON parsing errors handled gracefully
- ✅ Data validation catches malformed responses
- ✅ Fallback to cached data when appropriate
- ✅ Clear error logging for debugging

### Test Case: ERROR-004 - API Service Unavailability
**Objective**: Verify handling of API service downtime

**Pre-conditions**:
- Integration operational
- Ability to simulate API downtime

**Test Steps**:
1. Simulate API returning 503 Service Unavailable
2. Monitor integration behavior
3. Verify fallback mechanisms
4. Test recovery when service returns

**Expected Results**:
- ✅ Service unavailable errors handled properly
- ✅ Cached data continues to be served
- ✅ Retry mechanism with appropriate intervals
- ✅ No integration crashes or hangs

## Performance Tests

### Test Case: PERF-001 - Large Dataset Handling
**Objective**: Verify performance with large amounts of financial data

**Pre-conditions**:
- Account with extensive transaction history
- Multiple accounts configured

**Test Steps**:
1. Configure integration with accounts having large datasets
2. Monitor memory usage during data retrieval
3. Measure API response times
4. Verify pagination efficiency

**Expected Results**:
- ✅ Memory usage remains reasonable
- ✅ API calls complete within timeout limits
- ✅ Pagination handles large datasets efficiently
- ✅ No memory leaks during extended operation

**Performance Monitoring**:
```bash
# Monitor memory usage
ps aux | grep hass

# Check API response times in logs
grep "response_time" /config/home-assistant.log
```

### Test Case: PERF-002 - Concurrent API Requests
**Objective**: Verify handling of multiple simultaneous API requests

**Pre-conditions**:
- Multiple sensors configured
- Concurrent update scenarios

**Test Steps**:
1. Configure multiple sensors with similar update intervals
2. Trigger simultaneous updates
3. Monitor API request patterns
4. Verify request coordination

**Expected Results**:
- ✅ API requests properly coordinated
- ✅ No duplicate requests for same data
- ✅ Rate limiting respected across all requests
- ✅ Efficient use of API quota

## Cache Validation Tests

### Test Case: CACHE-001 - Cache Functionality
**Objective**: Verify caching mechanism improves performance

**Pre-conditions**:
- Caching enabled in configuration
- Fresh installation with no cached data

**Test Steps**:
1. Perform initial data retrieval (cache miss)
2. Immediately request same data (cache hit)
3. Compare response times
4. Verify cache TTL behavior

**Expected Results**:
- ✅ Cache miss results in API call
- ✅ Cache hit avoids API call
- ✅ Cached data served faster than API calls
- ✅ Cache expires according to TTL settings

### Test Case: CACHE-002 - Cache Invalidation
**Objective**: Verify cache invalidation works correctly

**Pre-conditions**:
- Data cached from previous operations
- Cache invalidation service available

**Test Steps**:
1. Verify data is cached
2. Call cache invalidation service
3. Verify cache is cleared
4. Confirm next request fetches fresh data

**Expected Results**:
- ✅ Cache invalidation service works
- ✅ Cached data properly removed
- ✅ Fresh API calls made after invalidation
- ✅ New data cached correctly

## Data Accuracy Tests

### Test Case: ACCURACY-001 - Currency Parsing
**Objective**: Verify accurate parsing of various currency formats

**Pre-conditions**:
- API returns various currency formats
- Different locale settings

**Test Steps**:
1. Test with USD format ($1,234.56)
2. Test with EUR format (1.234,56€)
3. Test with negative amounts
4. Test with zero amounts

**Expected Results**:
- ✅ All currency formats parsed correctly
- ✅ Negative amounts handled properly
- ✅ Zero amounts displayed correctly
- ✅ Currency symbols preserved in display

### Test Case: ACCURACY-002 - Date Handling
**Objective**: Verify accurate handling of date ranges and timezones

**Pre-conditions**:
- Various date formats in API responses
- Different timezone configurations

**Test Steps**:
1. Configure different timezone settings
2. Request data for specific date ranges
3. Verify date parsing accuracy
4. Check timezone conversion correctness

**Expected Results**:
- ✅ Date ranges respected in API calls
- ✅ Timezone conversions accurate
- ✅ Date formatting consistent
- ✅ Historical data retrieved correctly

## Integration Tests

### Test Case: INTEGRATION-001 - Home Assistant Services
**Objective**: Verify custom services function correctly

**Pre-conditions**:
- Integration loaded successfully
- Services registered in Home Assistant

**Test Steps**:
1. Call `sure_finance.refresh_data` service
2. Monitor logs for service execution
3. Verify data refresh occurs
4. Call `sure_finance.clear_cache` service
5. Verify cache clearing

**Expected Results**:
- ✅ Services appear in Developer Tools
- ✅ Service calls execute without errors
- ✅ Expected actions performed
- ✅ Service responses logged appropriately

### Test Case: INTEGRATION-002 - Entity State Management
**Objective**: Verify entity states update correctly

**Pre-conditions**:
- Entities created successfully
- Initial state data available

**Test Steps**:
1. Record initial entity states
2. Trigger data update
3. Verify state changes
4. Check entity attributes

**Expected Results**:
- ✅ Entity states update after data refresh
- ✅ State values accurate and formatted correctly
- ✅ Entity attributes contain relevant metadata
- ✅ State history preserved correctly

## Test Execution Checklist

### Pre-Test Setup
- [ ] Test environment configured
- [ ] Debug logging enabled
- [ ] Test credentials validated
- [ ] Baseline data recorded

### Authentication Tests
- [ ] AUTH-001: Valid API key authentication
- [ ] AUTH-002: Invalid API key handling
- [ ] AUTH-003: API key permission validation

### Data Retrieval Tests
- [ ] DATA-001: Account data retrieval
- [ ] DATA-002: Transaction data retrieval
- [ ] DATA-003: Financial metrics calculation

### Error Handling Tests
- [ ] ERROR-001: Network connectivity issues
- [ ] ERROR-002: API rate limiting
- [ ] ERROR-003: Malformed API responses
- [ ] ERROR-004: API service unavailability

### Performance Tests
- [ ] PERF-001: Large dataset handling
- [ ] PERF-002: Concurrent API requests

### Cache Validation Tests
- [ ] CACHE-001: Cache functionality
- [ ] CACHE-002: Cache invalidation

### Data Accuracy Tests
- [ ] ACCURACY-001: Currency parsing
- [ ] ACCURACY-002: Date handling

### Integration Tests
- [ ] INTEGRATION-001: Home Assistant services
- [ ] INTEGRATION-002: Entity state management

## Test Results Documentation

### Test Report Template
```
Test Case: [TEST_ID]
Date: [DATE]
Tester: [NAME]
Environment: [ENVIRONMENT_DETAILS]

Test Steps Executed:
1. [STEP_1]
2. [STEP_2]
...

Actual Results:
[DETAILED_RESULTS]

Pass/Fail: [STATUS]
Notes: [ADDITIONAL_OBSERVATIONS]
```

### Common Issues and Resolutions

**Issue**: API timeout errors
**Resolution**: Increase timeout values in configuration

**Issue**: Cache not working
**Resolution**: Verify Redis connectivity and configuration

**Issue**: Incorrect financial calculations
**Resolution**: Check transaction categorization and account type mapping

**Issue**: Entity not updating
**Resolution**: Verify update coordinator configuration and API connectivity

---

*These validation tests ensure comprehensive verification of the Sure Finance API integration functionality, covering all critical scenarios for reliable operation.*