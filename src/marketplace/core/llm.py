"""
LLM-based parameter extraction for intelligent task parsing.
Uses manifest input_schema when available, falls back to built-in hints.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from marketplace.settings import OLLAMA_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)

# Fallback when manifest has no input_schema
APP_PARAMETER_HINTS: Dict[str, List[str]] = {
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

EXAMPLE_TEMPLATES: Dict[str, str] = {
    "coinbase_prices": """Examples:
"Get XRP price in USD" → {{"currency_pair": "XRP-USD"}}
"Bitcoin price" → {{"currency_pair": "BTC-USD"}}
"ETH in EUR" → {{"currency_pair": "ETH-EUR"}}""",
    "coingecko_crypto": """Examples:
"Get XRP price in USD" → {{"coin_id": "ripple", "vs_currency": "usd"}}
"Bitcoin price" → {{"coin_id": "bitcoin", "vs_currency": "usd"}}
"ETH in EUR" → {{"coin_id": "ethereum", "vs_currency": "eur"}}""",
    "wikipedia_search": """Examples:
"Search for Eiffel Tower" → {{"q": "Eiffel Tower"}}
"Tell me about Albert Einstein" → {{"q": "Albert Einstein"}}
"What is quantum physics" → {{"q": "quantum physics"}}""",
    "placeholder_images": """Examples:
"Get a cat picture" → {{"width": 400, "height": 300}}
"Random image 800x600" → {{"width": 800, "height": 600}}
"Placeholder image" → {{"width": 400, "height": 300}}""",
}


def extract_parameters_from_task(
    task: str,
    app_id: str,
    executor_url: str,
    input_schema: Optional[Dict[str, Any]] = None,
) -> Optional[Dict]:
    """
    Use LLM to intelligently extract parameters from a natural language task.

    Args:
        task: Natural language task description
        app_id: The app being executed
        executor_url: The provider endpoint URL
        input_schema: Optional manifest input_schema with {parameters: [...], examples: "..."}

    Returns:
        Dictionary of extracted parameters, or None if extraction fails
    """
    if input_schema and isinstance(input_schema.get("parameters"), list):
        expected_params = input_schema["parameters"]
        examples = input_schema.get("examples") or "No examples available for this API."
    else:
        expected_params = APP_PARAMETER_HINTS.get(app_id, [])
        examples = EXAMPLE_TEMPLATES.get(app_id, "No examples available for this API.")

    if not expected_params:
        return None

    prompt = f"""Extract parameters for the {app_id} API from this query. Return ONLY JSON.

Query: "{task}"
Required parameters: {', '.join(expected_params)}

{examples}

IMPORTANT: Use ONLY these parameter names: {', '.join(expected_params)}
For currency_pair format: "SYMBOL-CURRENCY" (e.g., "XRP-USD")
For coin_id: XRP="ripple", Bitcoin="bitcoin", ETH="ethereum"

JSON:"""

    llm_output = ""
    try:
        import requests

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.1,
            },
            timeout=10,
        )

        if not response.ok:
            logger.warning(f"LLM request failed: {response.status_code}")
            return None

        data = response.json()
        llm_output = data.get("response", "").strip()

        # Handle markdown code blocks
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
        logger.debug("LLM output was: %s", llm_output)
        return None
    except Exception as e:
        logger.warning(f"Parameter extraction failed: {e}")
        return None
