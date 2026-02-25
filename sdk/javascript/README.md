# Axiomeer JavaScript/TypeScript SDK

Official JavaScript/TypeScript client for the [Axiomeer AI Agent Marketplace](https://axiomeer.com).

Discover and execute tools, APIs, RAG systems, datasets, and more through natural language.

## Installation

```bash
npm install @axiomeer/sdk
# or
yarn add @axiomeer/sdk
```

## Quick Start

```typescript
import { AgentMarketplace } from '@axiomeer/sdk';

// Initialize client
const marketplace = new AgentMarketplace({
  apiKey: 'axm_your_api_key_here'
});

// Shop for a tool
const result = await marketplace.shop('I need weather information');

// Execute the tool
const execution = await marketplace.execute(result.selected_app.app_id, {
  location: 'New York'
});

console.log(execution.result);
```

## Authentication

Get your API key from the [Axiomeer Dashboard](https://axiomeer.com/dashboard):

```typescript
// Option 1: Pass directly
const marketplace = new AgentMarketplace({
  apiKey: 'axm_xxx'
});

// Option 2: Use environment variable AXIOMEER_API_KEY
const marketplace = new AgentMarketplace();
```

## Usage Examples

### Basic Shopping and Execution

```typescript
import { AgentMarketplace } from '@axiomeer/sdk';

const marketplace = new AgentMarketplace();

// Find a tool
const result = await marketplace.shop('I need to send SMS messages');

console.log(`Selected: ${result.selected_app.name}`);
console.log(`Confidence: ${(result.confidence * 100).toFixed(0)}%`);

// Execute the tool
const execution = await marketplace.execute(result.selected_app.app_id, {
  to: '+1234567890',
  message: 'Hello from Axiomeer!'
});

if (execution.success) {
  console.log('Success!', execution.result);
} else {
  console.error('Failed:', execution.error);
}
```

### Shop and Execute in One Call

```typescript
// Convenient shorthand
const result = await marketplace.shopAndExecute(
  'I need weather data',
  { location: 'Tokyo' }
);

console.log(result.result);
```

### Advanced Shopping with Filters

```typescript
const result = await marketplace.shop(
  'I need to translate text',
  {
    required_capabilities: ['translation', 'multilingual'],
    excluded_providers: ['unreliable-translator'],
    max_cost_usd: 0.01
  }
);

// Check alternatives
result.alternatives.forEach(alt => {
  console.log(`Alternative: ${alt.name} by ${alt.provider}`);
});
```

### List Available Apps

```typescript
const apps = await marketplace.listApps({
  category: 'weather',
  limit: 10
});

apps.forEach(app => {
  console.log(`${app.name}: ${app.description}`);
  console.log(`  Provider: ${app.provider}`);
  console.log(`  Capabilities: ${app.capabilities.join(', ')}`);
});
```

### Error Handling

```typescript
import {
  AgentMarketplace,
  AuthenticationError,
  RateLimitError,
  ExecutionError
} from '@axiomeer/sdk';

try {
  const marketplace = new AgentMarketplace();
  const result = await marketplace.shop('I need to process images');
  const execution = await marketplace.execute(result.selected_app.app_id, {
    image_url: 'https://example.com/photo.jpg'
  });

} catch (error) {
  if (error instanceof AuthenticationError) {
    console.error('Invalid API key');
  } else if (error instanceof RateLimitError) {
    console.error(`Rate limited. Retry after ${error.retryAfter}s`);
  } else if (error instanceof ExecutionError) {
    console.error('Execution failed:', error.message);
    console.error('Details:', error.details);
  }
}
```

### TypeScript Support

The SDK is written in TypeScript and provides full type definitions:

```typescript
import { AgentMarketplace, ShopResult, ExecutionResult, AppListing } from '@axiomeer/sdk';

const marketplace = new AgentMarketplace();

const shopResult: ShopResult = await marketplace.shop('I need weather');
const app: AppListing = shopResult.selected_app;
const execution: ExecutionResult = await marketplace.execute(app.app_id, {});
```

## API Reference

### AgentMarketplace

Main client for interacting with Axiomeer.

#### Constructor

```typescript
new AgentMarketplace(config?: AxiomeerConfig)
```

**Config options:**
- `apiKey` (string): Your Axiomeer API key
- `baseUrl` (string): API base URL (default: http://localhost:8000)
- `timeout` (number): Request timeout in milliseconds (default: 30000)

#### Methods

##### `shop(task, options?)`

Find the best tool for your task.

**Returns:** `Promise<ShopResult>`

##### `execute(appId, params?)`

Execute a tool with given parameters.

**Returns:** `Promise<ExecutionResult>`

##### `shopAndExecute(task, params?)`

Shop and execute in one call.

**Returns:** `Promise<ExecutionResult>`

##### `listApps(params?)`

List available applications.

**Returns:** `Promise<AppListing[]>`

##### `health()`

Check API health status.

**Returns:** `Promise<HealthResponse>`

## Types

### ShopResult

```typescript
interface ShopResult {
  selected_app: AppListing;
  reasoning: string;
  confidence: number;
  alternatives: AppListing[];
}
```

### ExecutionResult

```typescript
interface ExecutionResult {
  success: boolean;
  result: any;
  app_id: string;
  execution_time_ms?: number;
  cost_usd?: number;
  error?: string;
}
```

### AppListing

```typescript
interface AppListing {
  app_id: string;
  name: string;
  description: string;
  provider: string;
  capabilities: string[];
  trust_card?: Record<string, any>;
  category?: string;
  uptime?: number;
}
```

## Environment Variables

- `AXIOMEER_API_KEY`: Your API key
- `AXIOMEER_BASE_URL`: Custom API base URL (default: http://localhost:8000)

## Framework Integration

### Express.js

```typescript
import express from 'express';
import { AgentMarketplace } from '@axiomeer/sdk';

const app = express();
const marketplace = new AgentMarketplace();

app.get('/weather/:city', async (req, res) => {
  const result = await marketplace.shopAndExecute(
    'I need weather information',
    { location: req.params.city }
  );
  res.json(result);
});
```

### Next.js

```typescript
// pages/api/tools/[task].ts
import { AgentMarketplace } from '@axiomeer/sdk';

export default async function handler(req, res) {
  const marketplace = new AgentMarketplace();
  const { task } = req.query;

  const result = await marketplace.shop(task);
  res.json(result);
}
```

## Support

- Documentation: https://docs.axiomeer.com
- Issues: https://github.com/axiomeer/axiomeer-sdk-js/issues
- Email: support@axiomeer.com

## License

MIT License - see [LICENSE](LICENSE) for details.
