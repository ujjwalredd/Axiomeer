"""
Advanced usage examples for Axiomeer Python SDK
"""

from axiomeer import (
    AgentMarketplace,
    AuthenticationError,
    RateLimitError,
    ExecutionError,
    NotFoundError
)
import time

# Initialize client
marketplace = AgentMarketplace()  # Uses AXIOMEER_API_KEY from environment

print("=" * 60)
print("Axiomeer Python SDK - Advanced Usage Examples")
print("=" * 60)
print()


# Example 1: Error Handling
print("Example 1: Comprehensive Error Handling")
print("-" * 60)

def safe_shop_and_execute(task, **params):
    """Safely shop and execute with full error handling"""
    try:
        # Shop for tool
        result = marketplace.shop(task)
        print(f"✓ Found: {result.selected_app.name}")

        # Execute tool
        execution = result.execute(marketplace, **params)

        if execution.success:
            print(f"✓ Success: {execution.result}")
            return execution.result
        else:
            print(f"✗ Execution failed: {execution.error}")
            return None

    except AuthenticationError:
        print("✗ Authentication failed. Check your API key.")
        return None
    except RateLimitError as e:
        print(f"✗ Rate limit exceeded. Retry after {e.retry_after} seconds")
        if e.retry_after:
            time.sleep(int(e.retry_after))
            return safe_shop_and_execute(task, **params)
        return None
    except ExecutionError as e:
        print(f"✗ Tool execution error: {e}")
        print(f"   Details: {e.details}")
        return None
    except NotFoundError:
        print(f"✗ No tool found for task: {task}")
        return None
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return None

# Test the error handling
safe_shop_and_execute("What's the weather in Tokyo?", location="Tokyo")
print()


# Example 2: Chaining Multiple Tools
print("Example 2: Chaining Multiple Tools")
print("-" * 60)

def get_weather_and_translate(city, target_language="Spanish"):
    """Get weather and translate the result"""

    # Step 1: Get weather
    print(f"Step 1: Getting weather for {city}...")
    weather_result = marketplace.shop("I need current weather")
    weather_exec = weather_result.execute(marketplace, location=city)

    if not weather_exec.success:
        print(f"✗ Weather lookup failed")
        return None

    weather_text = str(weather_exec.result)
    print(f"✓ Weather: {weather_text}")

    # Step 2: Translate result
    print(f"Step 2: Translating to {target_language}...")
    translate_result = marketplace.shop("I need to translate text")
    translate_exec = translate_result.execute(
        marketplace,
        text=weather_text,
        target_language=target_language
    )

    if translate_exec.success:
        print(f"✓ Translated: {translate_exec.result}")
        return translate_exec.result
    else:
        print(f"✗ Translation failed")
        return weather_text

get_weather_and_translate("London", "French")
print()


# Example 3: Parallel Tool Discovery
print("Example 3: Discovering Multiple Tools in Parallel")
print("-" * 60)

tasks = [
    "I need to get stock prices",
    "I need to send emails",
    "I need to process images",
]

print("Shopping for multiple tools:")
results = []
for task in tasks:
    try:
        result = marketplace.shop(task)
        results.append((task, result))
        print(f"  • {task[:30]}: → {result.selected_app.name}")
    except Exception as e:
        print(f"  • {task[:30]}: ✗ {e}")

print()


# Example 4: Comparing Alternatives
print("Example 4: Comparing Tool Alternatives")
print("-" * 60)

result = marketplace.shop("I need a database for storing data")

print(f"Primary: {result.selected_app.name}")
print(f"  Score: {result.confidence:.1%}")
print(f"  Reasoning: {result.reasoning}")
print()

if result.alternatives:
    print(f"Alternatives ({len(result.alternatives)}):")
    for i, alt in enumerate(result.alternatives[:5], 1):
        print(f"  {i}. {alt.name}")
        print(f"     Provider: {alt.provider}")
        print(f"     Capabilities: {', '.join(alt.capabilities[:3])}")
        print()


# Example 5: Dynamic Tool Selection
print("Example 5: Dynamic Tool Selection Based on Context")
print("-" * 60)

def smart_data_retrieval(query):
    """Choose the right tool based on query type"""

    query_lower = query.lower()

    # Determine tool type needed
    if "weather" in query_lower:
        tool_task = "I need weather information"
    elif "wikipedia" in query_lower or "definition" in query_lower:
        tool_task = "I need encyclopedia information"
    elif "news" in query_lower:
        tool_task = "I need current news"
    else:
        tool_task = "I need general information retrieval"

    print(f"Query: {query}")
    print(f"Selected strategy: {tool_task}")

    # Shop and execute
    result = marketplace.shop(tool_task)
    print(f"Using tool: {result.selected_app.name}")

    execution = result.execute(marketplace, query=query)

    if execution.success:
        print(f"✓ Result: {str(execution.result)[:100]}...")
        return execution.result
    else:
        print(f"✗ Failed: {execution.error}")
        return None

# Test different queries
queries = [
    "What's the weather in Paris?",
    "What is machine learning?",
    "Latest news about AI"
]

for query in queries:
    smart_data_retrieval(query)
    print()


# Example 6: Tool Performance Monitoring
print("Example 6: Monitoring Tool Performance")
print("-" * 60)

def execute_with_metrics(app_id, params, iterations=3):
    """Execute a tool multiple times and collect metrics"""

    print(f"Testing {app_id} with {iterations} iterations...")

    times = []
    successes = 0

    for i in range(iterations):
        start = time.time()
        execution = marketplace.execute(app_id, params)
        elapsed = (time.time() - start) * 1000  # Convert to ms

        times.append(elapsed)
        if execution.success:
            successes += 1

    avg_time = sum(times) / len(times)
    success_rate = (successes / iterations) * 100

    print(f"  Success rate: {success_rate:.1f}%")
    print(f"  Avg time: {avg_time:.2f}ms")
    print(f"  Min/Max: {min(times):.2f}ms / {max(times):.2f}ms")
    print()

# Test performance
execute_with_metrics("wikipedia", {"query": "Python programming"}, iterations=3)


print("=" * 60)
print("Advanced examples completed!")
print("=" * 60)
