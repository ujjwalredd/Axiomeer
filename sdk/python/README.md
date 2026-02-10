# Axiomeer Python SDK

[![PyPI version](https://img.shields.io/pypi/v/axiomeer.svg)](https://pypi.org/project/axiomeer/)
[![Python](https://img.shields.io/pypi/pyversions/axiomeer.svg)](https://pypi.org/project/axiomeer/)
[![License](https://img.shields.io/pypi/l/axiomeer.svg)](https://github.com/ujjwalredd/Axiomeer/blob/main/LICENSE)

Official Python client for the [Axiomeer AI Agent Marketplace](https://github.com/ujjwalredd/Axiomeer).

Discover and execute tools, APIs, RAG systems, datasets, and more through natural language.

## Installation

```bash
pip install axiomeer
```

Or install from source:

```bash
git clone https://github.com/ujjwalredd/axiomeer.git
cd axiomeer/sdk/python/
pip install -e .
```

## Quick Start

```python
from axiomeer import AgentMarketplace

# Initialize client with your API key
marketplace = AgentMarketplace(api_key="axm_your_api_key_here")

# Shop for a tool using natural language
result = marketplace.shop("I need to get weather information")

# Execute the selected tool
execution = result.execute(marketplace, location="New York")

print(f"Weather: {execution.result}")
```

## Authentication

Get your API key from [Axiomeer](https://github.com/ujjwalredd/Axiomeer):

```python
# Option 1: Pass directly
marketplace = AgentMarketplace(api_key="axm_xxx")

# Option 2: Use environment variable
import os
os.environ["AXIOMEER_API_KEY"] = "axm_xxx"
marketplace = AgentMarketplace()  # Auto-loads from env
```

## Usage Examples

### Basic Shopping

```python
# Find a tool for your task
result = marketplace.shop("I need to send SMS messages")

print(f"Selected: {result.selected_app.name}")
print(f"Reasoning: {result.reasoning}")
print(f"Confidence: {result.confidence:.2%}")

# Execute the tool
execution = result.execute(
    marketplace,
    to="+1234567890",
    message="Hello from Axiomeer!"
)

if execution.success:
    print(f"Success! Result: {execution.result}")
else:
    print(f"Failed: {execution.error}")
```

### Advanced Shopping with Filters

```python
# Shop with specific requirements
result = marketplace.shop(
    task="I need weather data",
    required_capabilities=["real-time", "global"],
    excluded_providers=["unreliable-weather"],
    max_cost_usd=0.01
)

# Check alternatives
for alt in result.alternatives:
    print(f"Alternative: {alt.name} by {alt.provider}")
```

### Direct Execution

```python
# Execute a tool directly by app_id
execution = marketplace.execute(
    app_id="weather-api-openweather",
    params={"location": "San Francisco", "units": "metric"}
)

print(execution.result)
```

### List Available Apps

```python
# Browse marketplace
apps = marketplace.list_apps(category="weather", limit=10)

for app in apps:
    print(f"{app.name}: {app.description}")
    print(f"  Provider: {app.provider}")
    print(f"  Capabilities: {', '.join(app.capabilities)}")
    print()
```

### Error Handling

```python
from axiomeer import (
    AgentMarketplace,
    AuthenticationError,
    RateLimitError,
    ExecutionError
)

try:
    marketplace = AgentMarketplace(api_key="axm_xxx")
    result = marketplace.shop("I need to process images")
    execution = result.execute(marketplace, image_url="https://example.com/photo.jpg")

except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limit exceeded. Retry after {e.retry_after} seconds")
except ExecutionError as e:
    print(f"Tool execution failed: {e}")
    print(f"Details: {e.details}")
```

## API Reference

### AgentMarketplace

Main client for interacting with Axiomeer.

#### `__init__(api_key, base_url, timeout)`

- `api_key` (str): Your Axiomeer API key
- `base_url` (str, optional): API base URL (default: http://localhost:8000)
- `timeout` (int, optional): Request timeout in seconds (default: 30)

#### `shop(task, required_capabilities, excluded_providers, max_cost_usd)`

Find the best tool for your task.

**Returns:** `ShopResult`

#### `execute(app_id, params)`

Execute a tool with given parameters.

**Returns:** `ExecutionResult`

#### `list_apps(category, search, limit)`

List available applications.

**Returns:** `List[AppListing]`

#### `health()`

Check API health status.

**Returns:** `Dict[str, Any]`

## Models

### ShopResult

Result from shopping for a tool.

**Attributes:**
- `selected_app` (AppListing): The recommended tool
- `reasoning` (str): Why this tool was selected
- `confidence` (float): Confidence score (0.0 - 1.0)
- `alternatives` (List[AppListing]): Alternative tools

**Methods:**
- `execute(marketplace, **params)`: Execute the selected tool

### ExecutionResult

Result from executing a tool.

**Attributes:**
- `success` (bool): Whether execution succeeded
- `result` (Any): The execution result
- `app_id` (str): Tool that was executed
- `execution_time_ms` (float): Execution time
- `cost_usd` (float): Cost in USD
- `error` (str): Error message if failed

### AppListing

Represents a tool in the marketplace.

**Attributes:**
- `app_id` (str): Unique identifier
- `name` (str): Tool name
- `description` (str): Tool description
- `provider` (str): Provider name
- `capabilities` (List[str]): List of capabilities
- `trust_card` (Dict): Trust and security information
- `category` (str): Tool category
- `uptime` (float): Uptime percentage

## Environment Variables

- `AXIOMEER_API_KEY`: Your API key (alternative to passing it directly)
- `AXIOMEER_BASE_URL`: Custom API base URL (default: http://localhost:8000)

## Support

- Documentation: https://github.com/ujjwalredd/Axiomeer#readme
- Issues: https://github.com/ujjwalredd/Axiomeer/issues

## License

MIT License - see [LICENSE](LICENSE) for details.
