/**
 * Basic usage examples for Axiomeer JavaScript SDK
 *
 * Run with: node examples/basic-usage.js
 * Prerequisites:
 * - npm install
 * - export AXIOMEER_API_KEY=axm_xxx
 * - API running at http://localhost:8000
 */

const { AgentMarketplace } = require('../dist');

async function main() {
  console.log('='.repeat(60));
  console.log('Axiomeer JavaScript SDK - Basic Usage Examples');
  console.log('='.repeat(60));
  console.log();

  // Initialize marketplace
  const marketplace = new AgentMarketplace({
    baseUrl: process.env.AXIOMEER_BASE_URL || 'http://localhost:8000'
  });

  // Example 1: Shop for weather tool
  console.log('Example 1: Shopping for Weather Tool');
  console.log('-'.repeat(60));

  try {
    const result = await marketplace.shop('I need current weather information');

    console.log(`✓ Selected: ${result.selected_app.name}`);
    console.log(`  Provider: ${result.selected_app.provider}`);
    console.log(`  Reasoning: ${result.reasoning}`);
    console.log(`  Confidence: ${(result.confidence * 100).toFixed(1)}%`);
    console.log();

    // Execute the tool
    console.log('Executing weather lookup for New York...');
    const execution = await marketplace.execute(result.selected_app.app_id, {
      location: 'New York'
    });

    if (execution.success) {
      console.log(`✓ Success!`);
      console.log(`  Result: ${execution.result}`);
      if (execution.execution_time_ms) {
        console.log(`  Time: ${execution.execution_time_ms.toFixed(2)}ms`);
      }
    } else {
      console.log(`✗ Failed: ${execution.error}`);
    }
  } catch (error) {
    console.error(`✗ Error: ${error.message}`);
  }

  console.log();

  // Example 2: Shop and execute in one call
  console.log('Example 2: Shop and Execute in One Call');
  console.log('-'.repeat(60));

  try {
    const result = await marketplace.shopAndExecute(
      'I need information from Wikipedia',
      { query: 'Artificial Intelligence' }
    );

    if (result.success) {
      const resultText = String(result.result);
      console.log(`✓ Success!`);
      console.log(`  Result: ${resultText.substring(0, 200)}...`);
    } else {
      console.log(`✗ Failed: ${result.error}`);
    }
  } catch (error) {
    console.error(`✗ Error: ${error.message}`);
  }

  console.log();

  // Example 3: List available apps
  console.log('Example 3: Browse Available Tools');
  console.log('-'.repeat(60));

  try {
    const apps = await marketplace.listApps({ limit: 5 });

    console.log(`✓ Found ${apps.length} tools:`);
    console.log();

    apps.forEach((app, i) => {
      console.log(`${i + 1}. ${app.name}`);
      console.log(`   Provider: ${app.provider}`);
      console.log(`   Description: ${app.description.substring(0, 80)}...`);
      if (app.capabilities.length > 0) {
        console.log(`   Capabilities: ${app.capabilities.slice(0, 3).join(', ')}`);
      }
      console.log();
    });
  } catch (error) {
    console.error(`✗ Error: ${error.message}`);
  }

  // Example 4: Health check
  console.log('Example 4: Health Check');
  console.log('-'.repeat(60));

  try {
    const health = await marketplace.health();
    console.log(`✓ Status: ${health.status}`);
    console.log(`  Version: ${health.version || 'unknown'}`);
  } catch (error) {
    console.error(`✗ Error: ${error.message}`);
  }

  console.log();
  console.log('='.repeat(60));
  console.log('All examples completed successfully!');
  console.log('='.repeat(60));
}

main().catch(console.error);
