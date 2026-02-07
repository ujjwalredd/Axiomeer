"""
LLM-based parameter extraction for intelligent task parsing.
"""
import json
import logging
import requests
from typing import Dict, Optional

from marketplace.settings import OLLAMA_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)


def extract_parameters_from_task(task: str, app_id: str, executor_url: str) -> Optional[Dict]:
    """
    Use LLM to intelligently extract parameters from a natural language task.

    Args:
        task: Natural language task description
        app_id: The app being executed
        executor_url: The provider endpoint URL

    Returns:
        Dictionary of extracted parameters, or None if extraction fails
    """

    # Map app_id to expected parameters
    # This is just a hint for the LLM - not hardcoded extraction
    app_parameter_hints = {
        "coingecko_crypto": ["coin_id", "vs_currency"],
        "coinbase_prices": ["currency_pair"],
        "blockchain_info": ["endpoint"],
        "exchange_rates": ["base", "target"],
        "realtime_weather_agent": ["lat", "lon", "timezone_name"],
        "wikipedia_search": ["q"],
        "wikipedia_dumps": ["lang"],
        "wikidata_search": ["q"],
        "open_library": ["q"],
        "placeholder_images": ["width", "height"],
        "omdb_movies": ["t"],
        "tmdb_movies": ["query"],
        "arxiv_papers": ["search_query"],
        "pubmed_search": ["term"],
    }

    expected_params = app_parameter_hints.get(app_id, [])

    if not expected_params:
        # No extraction needed for this app
        return None

    # Build provider-specific examples
    if app_id == "coinbase_prices":
        examples = """Examples:
"Get XRP price in USD" → {{"currency_pair": "XRP-USD"}}
"Bitcoin price" → {{"currency_pair": "BTC-USD"}}
"ETH in EUR" → {{"currency_pair": "ETH-EUR"}}"""
    elif app_id == "coingecko_crypto":
        examples = """Examples:
"Get XRP price in USD" → {{"coin_id": "ripple", "vs_currency": "usd"}}
"Bitcoin price" → {{"coin_id": "bitcoin", "vs_currency": "usd"}}
"ETH in EUR" → {{"coin_id": "ethereum", "vs_currency": "eur"}}"""
    elif app_id == "wikipedia_search":
        examples = """Examples:
"Search for Eiffel Tower" → {{"q": "Eiffel Tower"}}
"Tell me about Albert Einstein" → {{"q": "Albert Einstein"}}
"What is quantum physics" → {{"q": "quantum physics"}}"""
    elif app_id == "placeholder_images":
        examples = """Examples:
"Get a cat picture" → {{"width": 400, "height": 300}}
"Random image 800x600" → {{"width": 800, "height": 600}}
"Placeholder image" → {{"width": 400, "height": 300}}"""
    else:
        examples = "No examples available for this API."

    prompt = f"""Extract parameters for the {app_id} API from this query. Return ONLY JSON.

Query: "{task}"
Required parameters: {', '.join(expected_params)}

{examples}

IMPORTANT: Use ONLY these parameter names: {', '.join(expected_params)}
For currency_pair format: "SYMBOL-CURRENCY" (e.g., "XRP-USD")
For coin_id: XRP="ripple", Bitcoin="bitcoin", ETH="ethereum"

JSON:"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.1,
            },
            timeout=10
        )

        if not response.ok:
            logger.warning(f"LLM request failed: {response.status_code}")
            return None

        data = response.json()
        llm_output = data.get("response", "").strip()

        # Try to parse JSON from LLM output
        # Handle cases where LLM adds markdown code blocks
        if "```json" in llm_output:
            llm_output = llm_output.split("```json")[1].split("```")[0].strip()
        elif "```" in llm_output:
            llm_output = llm_output.split("```")[1].split("```")[0].strip()

        extracted = json.loads(llm_output)

        if isinstance(extracted, dict) and extracted:
            logger.info(f"Extracted parameters for {app_id}: {extracted}")
            return extracted

        return None

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM output as JSON: {e}")
        logger.debug(f"LLM output was: {llm_output}")
        return None
    except Exception as e:
        logger.warning(f"Parameter extraction failed: {e}")
        return None
