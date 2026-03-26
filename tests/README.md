# Sure Finance Home Assistant Integration - Test Suite

This directory contains comprehensive automated test cases for the Sure Finance Home Assistant integration. The test suite covers unit tests, integration tests, and performance tests to ensure reliability and maintainability.

## 📝 Test Coverage

### Unit Tests
- **API Client Tests** (`test_api_client.py`) - Authentication, HTTP handling, error responses, rate limiting
- **Data Manager Tests** (`test_data_manager.py`) - Data synchronization, cache coordination, financial data aggregation
- **Financial Calculator Tests** (`test_financial_calculator.py`) - Net worth calculations, cashflow analysis, currency parsing
- **Cache Manager Tests** (`test_cache_manager.py`) - Multi-tier caching, TTL behavior, Redis integration
- **Config Flow Tests** (`test_config_flow.py`) - User input validation, configuration persistence, error handling
- **Sensor Tests** (`test_sensor.py`) - Entity creation, state management, update coordinator functionality
- **Model Tests** (`test_models.py`) - Pydantic model validation, serialization, edge cases

### Integration Tests
- **Integration Tests** (`test_integration.py`) - Setup/teardown processes, service registration, platform loading

## 🚀 Quick Start

### Prerequisites

1. **Python 3.11+** with pip
2. **Virtual Environment** (recommended)

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-test.txt
```

### Running Tests

#### Using the Test Runner (Recommended)

```bash
# Setup test environment
python tests/test_runner.py setup

# Run all tests and checks
python tests/test_runner.py all

# Run specific test types
python tests/test_runner.py unit          # Unit tests only
python tests/test_runner.py integration   # Integration tests only
python tests/test_runner.py lint          # Code quality checks
python tests/test_runner.py security      # Security vulnerability checks
python tests/test_runner.py coverage      # Generate coverage report

# Run specific test file
python tests/test_runner.py test tests/test_api_client.py

# Verbose output
python tests/test_runner.py unit -v
```

#### Using Pytest Directly

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=custom_components.sure_finance --cov-report=html

# Run specific test file
pytest tests/test_api_client.py

# Run specific test function
pytest tests/test_api_client.py::TestSureFinanceClient::test_successful_request

# Run tests with specific markers
pytest -m "not slow"           # Exclude slow tests
pytest -m "integration"        # Only integration tests
pytest -m "unit"               # Only unit tests
```

## 📁 Test Structure

```
tests/
├── conftest.py                 # Pytest configuration and shared fixtures
├── test_api_client.py          # API client unit tests
├── test_data_manager.py        # Data manager unit tests
├── test_financial_calculator.py # Financial calculator unit tests
├── test_cache_manager.py       # Cache manager unit tests
├── test_config_flow.py         # Config flow unit tests
├── test_sensor.py              # Sensor platform unit tests
├── test_models.py              # Pydantic models unit tests
├── test_integration.py         # Integration tests
├── test_runner.py              # Test runner script
└── README.md                   # This file
```

## 🧪 Fixtures and Test Data

The test suite uses comprehensive fixtures defined in `conftest.py`:

- **Mock Objects**: Home Assistant, config entries, API clients
- **Sample Data**: Accounts, transactions, categories, merchants
- **Test Utilities**: Currency parsing, decimal assertions, mock responses
- **Performance Data**: Large datasets for performance testing

### Key Fixtures

```python
# Mock Home Assistant instance
def mock_hass():
    return MagicMock(spec=HomeAssistant)

# Sample financial data
def sample_accounts():
    return [Account(...), Account(...)]

# Mock API responses
def mock_api_response_accounts():
    return {"accounts": [...], "pagination": {...}}

# Temporary cache directory
def temp_cache_dir(tmp_path):
    return tmp_path / "cache"
```

## 📊 Test Categories

### Unit Tests
Test individual components in isolation with mocked dependencies.

**Coverage Areas:**
- ✅ Authentication and authorization
- ✅ HTTP request/response handling
- ✅ Data validation and parsing
- ✅ Financial calculations
- ✅ Caching mechanisms
- ✅ Configuration validation
- ✅ Entity state management
- ✅ Error handling and edge cases

### Integration Tests
Test component interactions and end-to-end workflows.

**Coverage Areas:**
- ✅ Integration setup and teardown
- ✅ Service registration and removal
- ✅ Platform loading and unloading
- ✅ Data flow between components
- ✅ Error propagation and recovery

### Performance Tests
Test system performance under various loads.

**Coverage Areas:**
- ✅ Large dataset handling
- ✅ Concurrent request processing
- ✅ Memory usage optimization
- ✅ Cache performance
- ✅ API response times

## 🔍 Test Scenarios

### API Client Tests

#### Authentication Tests
- ✅ Valid API key authentication
- ✅ Invalid API key handling
- ✅ Missing API key error
- ✅ API key format validation

#### HTTP Handling Tests
- ✅ Successful requests (200, 201)
- ✅ Client errors (400, 401, 403, 404)
- ✅ Server errors (500, 502, 503)
- ✅ Network timeouts and connection errors
- ✅ Rate limiting (429) with retry logic
- ✅ Malformed JSON responses

#### Data Retrieval Tests
- ✅ Account listing with pagination
- ✅ Transaction filtering by date range
- ✅ Category and merchant data
- ✅ Large dataset handling
- ✅ Empty response handling

### Data Manager Tests

#### Caching Tests
- ✅ Cache hit scenarios
- ✅ Cache miss and API fallback
- ✅ Cache expiration handling
- ✅ Force refresh bypassing cache
- ✅ Error fallback to stale cache

#### Synchronization Tests
- ✅ Full data synchronization
- ✅ Incremental updates
- ✅ Concurrent access handling
- ✅ Data consistency validation
- ✅ Sync error recovery

### Financial Calculator Tests

#### Calculation Tests
- ✅ Net worth calculation (assets - liabilities)
- ✅ Cashflow analysis (income vs expenses)
- ✅ Savings rate calculation
- ✅ Category breakdown analysis
- ✅ Recurring transaction detection

#### Currency Tests
- ✅ Multiple currency format parsing
- ✅ Decimal precision handling
- ✅ Large number calculations
- ✅ Edge case values (zero, negative)

### Cache Manager Tests

#### Multi-tier Caching Tests
- ✅ Memory cache (L1)
- ✅ Redis cache (L2)
- ✅ File cache (L3)
- ✅ Cache tier fallback
- ✅ Cache coherency

#### TTL and Expiration Tests
- ✅ Time-based expiration
- ✅ Manual cache invalidation
- ✅ Namespace-based clearing
- ✅ Cleanup of expired entries

### Config Flow Tests

#### Validation Tests
- ✅ Required field validation
- ✅ API key format checking
- ✅ URL validation
- ✅ Numeric range validation
- ✅ Boolean option handling

#### Error Handling Tests
- ✅ Authentication failures
- ✅ Network connectivity issues
- ✅ Invalid configuration recovery
- ✅ User input sanitization

### Sensor Tests

#### Entity Tests
- ✅ Sensor creation and registration
- ✅ State value calculation
- ✅ Attribute population
- ✅ Device information
- ✅ Unique ID generation

#### Update Coordinator Tests
- ✅ Periodic data updates
- ✅ Manual refresh triggers
- ✅ Error state handling
- ✅ Coordinator lifecycle

## 🛠️ Test Configuration

### Pytest Configuration (`pytest.ini`)

```ini
[pytest]
addopts = 
    --strict-markers
    --cov=custom_components.sure_finance
    --cov-report=html:htmlcov
    --cov-report=term-missing
    --cov-fail-under=85
    --asyncio-mode=auto

markers =
    asyncio: async tests
    slow: slow running tests
    integration: integration tests
    unit: unit tests
    performance: performance tests
```

### Test Markers

- `@pytest.mark.asyncio` - Async test functions
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.performance` - Performance benchmarks
- `@pytest.mark.edge_case` - Edge case scenarios

## 📊 Coverage Requirements

- **Minimum Coverage**: 85%
- **Target Coverage**: 95%+
- **Critical Paths**: 100% (authentication, financial calculations)

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=custom_components.sure_finance --cov-report=html

# View report
open htmlcov/index.html

# Generate XML coverage report (for CI/CD)
pytest --cov=custom_components.sure_finance --cov-report=xml
```

## 🔒 Security Testing

### Vulnerability Scanning

```bash
# Security linting with Bandit
bandit -r custom_components/sure_finance/

# Dependency vulnerability check
safety check

# Run security checks via test runner
python tests/test_runner.py security
```

### Security Test Areas

- ✅ API key handling and storage
- ✅ Input sanitization
- ✅ SQL injection prevention
- ✅ XSS prevention
- ✅ Dependency vulnerabilities
- ✅ Secure communication (HTTPS)

## 🎨 Code Quality

### Linting and Formatting

```bash
# Code formatting with Black
black custom_components/ tests/

# Import sorting with isort
isort custom_components/ tests/

# Linting with flake8
flake8 custom_components/ tests/

# Type checking with mypy
mypy custom_components/

# Run all quality checks
python tests/test_runner.py lint
```

### Quality Standards

- **Code Formatting**: Black (line length: 88)
- **Import Sorting**: isort (profile: black)
- **Linting**: flake8 (max complexity: 10)
- **Type Checking**: mypy (strict mode)
- **Documentation**: Google-style docstrings

## 🚀 Continuous Integration

### GitHub Actions Workflow

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11, 3.12]
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: pip install -r requirements-test.txt
      - name: Run tests
        run: python tests/test_runner.py all
```

### Test Automation

- ✅ Automated test execution on PR/push
- ✅ Multi-Python version testing
- ✅ Coverage reporting to Codecov
- ✅ Security vulnerability scanning
- ✅ Code quality checks
- ✅ Performance regression detection

## 📝 Test Documentation

### Writing Tests

#### Test Naming Convention

```python
def test_should_return_accounts_when_api_key_is_valid():
    """Test that API returns accounts with valid authentication."""
    pass

def test_should_raise_auth_error_when_api_key_is_invalid():
    """Test that invalid API key raises AuthenticationError."""
    pass
```

#### Test Structure (AAA Pattern)

```python
def test_calculate_net_worth():
    """Test net worth calculation with assets and liabilities."""
    # Arrange
    calculator = FinancialCalculator()
    accounts = [create_asset_account(1000), create_liability_account(-500)]
    
    # Act
    result = calculator.calculate_net_worth(accounts)
    
    # Assert
    assert result == Decimal("500.00")
```

#### Async Test Example

```python
@pytest.mark.asyncio
async def test_api_client_authentication():
    """Test API client authentication flow."""
    client = SureFinanceClient(api_key="test_key")
    
    with patch('aiohttp.ClientSession.request') as mock_request:
        mock_request.return_value.__aenter__.return_value.status = 200
        mock_request.return_value.__aenter__.return_value.json.return_value = {}
        
        await client.connect()
        result = await client.get_accounts()
        
        assert result == {}
```

### Test Best Practices

1. **Test Isolation**: Each test should be independent
2. **Clear Naming**: Test names should describe the scenario
3. **Single Responsibility**: One assertion per test when possible
4. **Mock External Dependencies**: Don't hit real APIs in tests
5. **Use Fixtures**: Reuse common test data and setup
6. **Test Edge Cases**: Include boundary conditions and error scenarios
7. **Document Complex Tests**: Add docstrings explaining the test purpose

## 🔧 Debugging Tests

### Running Tests in Debug Mode

```bash
# Run with verbose output
pytest -v

# Run with debug output
pytest -s

# Run specific test with debugging
pytest tests/test_api_client.py::test_auth_error -v -s

# Use ipdb for interactive debugging
pytest --pdb
```

### Common Debug Scenarios

1. **Mock Not Working**: Check mock patch path
2. **Async Test Failing**: Ensure `@pytest.mark.asyncio`
3. **Fixture Not Found**: Check fixture scope and location
4. **Import Errors**: Verify PYTHONPATH and module structure

## 📈 Performance Testing

### Benchmark Tests

```python
@pytest.mark.performance
def test_cache_performance(benchmark):
    """Benchmark cache operations."""
    cache = CacheManager()
    
    def cache_operations():
        cache.set("key", "value")
        return cache.get("key")
    
    result = benchmark(cache_operations)
    assert result == "value"
```

### Performance Metrics

- **API Response Time**: < 2 seconds
- **Cache Hit Time**: < 10ms
- **Memory Usage**: < 50MB for 1000 transactions
- **Startup Time**: < 5 seconds

## 🔄 Test Maintenance

### Regular Tasks

1. **Update Test Dependencies**: Monthly
2. **Review Coverage Reports**: Weekly
3. **Update Test Data**: When API changes
4. **Performance Baseline Updates**: Quarterly
5. **Security Scan Reviews**: Monthly

### Test Refactoring

- Remove duplicate test code
- Update obsolete test scenarios
- Improve test performance
- Enhance test readability
- Update mocks for API changes

## 📞 Support

### Getting Help

- **Documentation**: Check this README and inline comments
- **Issues**: Create GitHub issue for test-related problems
- **Debugging**: Use verbose mode and debug output
- **Community**: Discuss in Home Assistant forums

### Contributing Tests

1. Follow existing test patterns
2. Ensure adequate coverage
3. Include both positive and negative test cases
4. Add performance tests for critical paths
5. Update documentation for new test scenarios

---

📝 **Note**: This test suite is designed to run in CI/CD environments and supports parallel execution for faster feedback cycles.
