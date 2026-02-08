"""
Basic usage examples for Axiomeer Python SDK
"""

from axiomeer import AgentMarketplace

# Initialize the marketplace client
# Make sure to set AXIOMEER_API_KEY environment variable or pass it directly
marketplace = AgentMarketplace(api_key="axm_your_api_key_here")

print("=" * 60)
print("Axiomeer Python SDK - Basic Usage Examples")
print("=" * 60)
print()

# Example 1: Shop for a weather tool
print("Example 1: Shopping for Weather Tool")
print("-" * 60)
result = marketplace.shop("I need current weather information")

print(f"✓ Selected: {result.selected_app.name}")
print(f"  Provider: {result.selected_app.provider}")
print(f"  Reasoning: {result.reasoning}")
print(f"  Confidence: {result.confidence:.1%}")
print()

# Example 2: Execute the weather tool
print("Example 2: Executing Weather Tool")
print("-" * 60)
execution = result.execute(marketplace, location="New York")

if execution.success:
    print(f"✓ Success!")
    print(f"  Result: {execution.result}")
    print(f"  Execution time: {execution.execution_time_ms:.2f}ms")
else:
    print(f"✗ Failed: {execution.error}")
print()

# Example 3: Direct execution by app_id
print("Example 3: Direct Execution")
print("-" * 60)
execution = marketplace.execute(
    app_id="wikipedia",
    params={"query": "Artificial Intelligence"}
)

if execution.success:
    print(f"✓ Success!")
    print(f"  Result: {execution.result[:200]}...")  # First 200 chars
else:
    print(f"✗ Failed: {execution.error}")
print()

# Example 4: Shop with specific requirements
print("Example 4: Shopping with Requirements")
print("-" * 60)
result = marketplace.shop(
    task="I need to translate text between languages",
    required_capabilities=["translation", "multilingual"],
    max_cost_usd=0.01
)

print(f"✓ Selected: {result.selected_app.name}")
print(f"  Alternatives: {len(result.alternatives)}")
for i, alt in enumerate(result.alternatives[:3], 1):
    print(f"    {i}. {alt.name} (by {alt.provider})")
print()

# Example 5: Browse marketplace
print("Example 5: Browsing Marketplace")
print("-" * 60)
apps = marketplace.list_apps(limit=5)

print(f"✓ Found {len(apps)} apps:")
for app in apps:
    print(f"  • {app.name}")
    print(f"    {app.description[:80]}...")
    print(f"    Capabilities: {', '.join(app.capabilities[:3])}")
    print()

# Example 6: Check API health
print("Example 6: Health Check")
print("-" * 60)
health = marketplace.health()
print(f"✓ Status: {health.get('status', 'unknown')}")
print(f"  Version: {health.get('version', 'unknown')}")
print()

print("=" * 60)
print("All examples completed successfully!")
print("=" * 60)
