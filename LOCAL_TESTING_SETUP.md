# Local Testing Setup Guide for Sure Finance Integration

This guide provides step-by-step instructions for setting up a local Home Assistant development environment to test the Sure Finance integration manually.

## Prerequisites

### System Requirements
- **Operating System**: Linux, macOS, or Windows with WSL2
- **Python**: 3.11 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: At least 2GB free space
- **Network**: Internet connectivity for API access

### Required Software
- Python 3.11+
- Git
- Docker (optional, for containerized testing)
- Redis (optional, for cache testing)
- Text editor or IDE (VS Code, PyCharm, etc.)

## Setup Methods

### Method 1: Home Assistant Core Development Environment

#### Step 1: Clone Home Assistant Core
```bash
git clone https://github.com/home-assistant/core.git
cd core
```

#### Step 2: Create Python Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Step 3: Install Home Assistant in Development Mode
```bash
pip install -e .
pip install -r requirements_dev.txt
```

#### Step 4: Create Configuration Directory
```bash
mkdir config
cd config
```

#### Step 5: Create Basic Configuration
Create `config/configuration.yaml`:
```yaml
# Basic Home Assistant configuration for testing
default_config:

logger:
  default: info
  logs:
    custom_components.sure_finance: debug
    homeassistant.components.config_flow: debug

# Enable frontend for testing
frontend:

# Enable API
api:

# Enable HTTP component
http:
  server_port: 8123
```

#### Step 6: Install Sure Finance Integration
```bash
mkdir -p custom_components
cp -r /path/to/sure-finance-hass-integration/custom_components/sure_finance custom_components/
```

#### Step 7: Start Home Assistant
```bash
cd ..
hass -c config
```

### Method 2: Home Assistant Container Development

#### Step 1: Create Project Directory
```bash
mkdir ha-sure-finance-test
cd ha-sure-finance-test
```

#### Step 2: Create Docker Compose File
Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  homeassistant:
    container_name: ha-sure-finance-test
    image: homeassistant/home-assistant:latest
    volumes:
      - ./config:/config
      - ./custom_components:/config/custom_components
      - /etc/localtime:/etc/localtime:ro
    restart: unless-stopped
    privileged: true
    network_mode: host
    environment:
      - TZ=America/New_York  # Adjust to your timezone

  redis:
    container_name: redis-sure-finance
    image: redis:alpine
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

#### Step 3: Create Configuration Structure
```bash
mkdir -p config custom_components
cp -r /path/to/sure-finance-hass-integration/custom_components/sure_finance custom_components/
```

#### Step 4: Create Configuration File
Create `config/configuration.yaml`:
```yaml
default_config:

logger:
  default: info
  logs:
    custom_components.sure_finance: debug

frontend:
api:
http:
  server_port: 8123
```

#### Step 5: Start Environment
```bash
docker-compose up -d
```

### Method 3: Home Assistant OS in Virtual Machine

#### Step 1: Download Home Assistant OS
- Download the appropriate image from [Home Assistant OS releases](https://github.com/home-assistant/operating-system/releases)
- Choose the image for your virtualization platform (VirtualBox, VMware, etc.)

#### Step 2: Create Virtual Machine
- Allocate at least 2GB RAM and 32GB storage
- Configure network adapter for internet access
- Boot from the Home Assistant OS image

#### Step 3: Initial Setup
- Wait for Home Assistant to start (can take 10-20 minutes)
- Access web interface at `http://[VM_IP]:8123`
- Complete initial setup wizard

#### Step 4: Enable SSH Access
- Install "SSH & Web Terminal" add-on from Supervisor
- Configure SSH access for file transfer

#### Step 5: Install Integration
- Use SSH/SCP to copy integration files to `/config/custom_components/sure_finance`
- Restart Home Assistant

## Integration Installation

### Manual Installation Steps

1. **Copy Integration Files**
   ```bash
   cp -r sure-finance-hass-integration/custom_components/sure_finance /config/custom_components/
   ```

2. **Verify File Structure**
   ```
   /config/custom_components/sure_finance/
   ├── __init__.py
   ├── api_client.py
   ├── cache_manager.py
   ├── config_flow.py
   ├── data_manager.py
   ├── financial_calculator.py
   ├── manifest.json
   ├── models.py
   ├── sensor.py
   ├── services.yaml
   └── strings.json
   ```

3. **Install Dependencies**
   ```bash
   pip install aiohttp>=3.9.0 pydantic>=2.5.0 python-dateutil>=2.8.2 redis>=5.0.0
   ```

4. **Restart Home Assistant**
   - Core: Restart the `hass` process
   - Container: `docker-compose restart homeassistant`
   - OS: Restart from Supervisor

## Configuration for Testing

### Enable Debug Logging
Add to `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.sure_finance: debug
    homeassistant.components.config_flow: debug
    homeassistant.helpers.entity: debug
```

### Configure Redis (Optional)
If testing caching with Redis:
```yaml
# In configuration.yaml or as environment variable
redis:
  host: localhost
  port: 6379
  db: 0
```

### Test API Credentials
Prepare test credentials:
- Sure Finance API key
- API host URL (e.g., `https://app.sure.am`)
- Test account with financial data

## Integration Setup Process

### Step 1: Access Home Assistant
- Navigate to `http://localhost:8123` (or your HA instance URL)
- Complete initial setup if first time

### Step 2: Add Integration
1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Sure Finance"
4. Click on the integration

### Step 3: Configure Integration
1. Enter **API Key** from your Sure Finance account
2. Enter **API Host** (default: `https://app.sure.am`)
3. Configure optional settings:
   - Update interval (300-3600 seconds)
   - Currency code (USD, EUR, etc.)
   - Enable/disable specific sensors
   - Cache duration (300-86400 seconds)

### Step 4: Verify Installation
1. Check **Settings** → **Devices & Services** for Sure Finance entry
2. Verify entities are created:
   - `sensor.sure_finance_net_worth`
   - `sensor.sure_finance_total_cashflow`
   - `sensor.sure_finance_total_outflow`
   - `sensor.sure_finance_total_liability`
   - `sensor.sure_finance_monthly_savings_rate`

## Testing Environment Validation

### Verify Integration Loading
```bash
# Check Home Assistant logs
tail -f /config/home-assistant.log | grep sure_finance
```

### Test API Connectivity
```python
# Test script to verify API access
import asyncio
import aiohttp

async def test_api():
    async with aiohttp.ClientSession() as session:
        headers = {'Authorization': 'Bearer YOUR_API_KEY'}
        async with session.get('https://app.sure.am/api/accounts', headers=headers) as resp:
            print(f"Status: {resp.status}")
            data = await resp.json()
            print(f"Response: {data}")

asyncio.run(test_api())
```

### Verify Entity Creation
1. Navigate to **Developer Tools** → **States**
2. Search for `sure_finance` entities
3. Verify entities have valid states and attributes

### Test Services
1. Go to **Developer Tools** → **Services**
2. Test `sure_finance.refresh_data` service
3. Test `sure_finance.clear_cache` service
4. Monitor logs for service execution

## Troubleshooting Common Setup Issues

### Integration Not Loading
- **Check logs**: Look for Python import errors
- **Verify dependencies**: Ensure all required packages are installed
- **File permissions**: Ensure files are readable by HA process

### Configuration Flow Not Appearing
- **Clear browser cache**: Force refresh the integrations page
- **Check manifest.json**: Verify `config_flow: true` is set
- **Restart HA**: Ensure integration is properly loaded

### API Connection Issues
- **Network connectivity**: Test API endpoint manually
- **Firewall settings**: Ensure outbound HTTPS is allowed
- **SSL certificates**: Verify certificate validity

### Entity Creation Failures
- **Check sensor.py**: Look for entity creation errors
- **API data format**: Verify API returns expected data structure
- **Unique IDs**: Ensure entity unique IDs are properly generated

## Development Tools

### VS Code Extensions
- Python
- Home Assistant Config Helper
- YAML
- Docker

### Useful Commands
```bash
# Check integration status
hass --script check_config

# Validate manifest.json
python -m json.tool custom_components/sure_finance/manifest.json

# Test Python syntax
python -m py_compile custom_components/sure_finance/*.py

# Monitor logs in real-time
tail -f /config/home-assistant.log | grep -E "(sure_finance|ERROR|WARNING)"
```

## Next Steps

Once the local testing environment is set up:
1. Proceed with manual testing procedures
2. Execute automated test cases
3. Validate API integration functionality
4. Test error handling scenarios
5. Verify performance characteristics

---

*This setup guide ensures a proper testing environment for thorough validation of the Sure Finance integration before HACS deployment.*