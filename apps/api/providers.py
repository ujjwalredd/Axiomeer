"""
Provider endpoints for the AI Marketplace.

This module implements 52+ free API provider endpoints organized by category:
- NASA (3): APOD, Mars Rover, Asteroids
- Government Data (8): Census, World Bank, FRED, IMF, EU, UK Police, COVID, Data.gov
- Knowledge/Research (8): arXiv, PubMed, Semantic Scholar, Crossref, Wikidata, DBpedia, Archive.org, Gutenberg
- Financial/Crypto (3): CoinGecko, Coinbase, Blockchain.com
- Geographic (3): Nominatim, GeoNames, IP Geolocation
- Media (6): OMDB, TMDB, MusicBrainz, Genius, Unsplash, Pexels
- Language (2): LibreTranslate, Datamuse
- Utilities (7): Random User, Random Data, QR Code, Lorem Picsum, Jokes, Trivia, Bored API
- Hugging Face (8): GPT-2, Sentiment, Translation, Summarization, QA, NER, Image Classification
- Ollama (4): Llama 3.1, Mistral, CodeLlama, Deepseek Coder

All endpoints return a standardized response format with proper error handling,
caching, logging, and type hints.
"""

import json
import logging
from datetime import datetime, timezone
from time import time
from typing import Any, Dict, Optional
from threading import Lock

import requests
from fastapi import APIRouter, HTTPException, Query

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Create router
router = APIRouter(prefix="/providers", tags=["providers"])

# Cache configuration
_cache_lock = Lock()
_cache_store: Dict[str, Dict[str, Any]] = {}

# Cache TTL values (in seconds)
CACHE_TTL_SHORT = 300  # 5 minutes
CACHE_TTL_MEDIUM = 1800  # 30 minutes
CACHE_TTL_LONG = 3600  # 1 hour
CACHE_TTL_DAILY = 86400  # 24 hours

# HTTP timeout
DEFAULT_TIMEOUT = 10


def _cache_key(prefix: str, payload: Dict[str, Any]) -> str:
    """Generate a cache key from prefix and payload."""
    return f"{prefix}:{json.dumps(payload, sort_keys=True, default=str)}"


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    """Retrieve value from cache if not expired."""
    with _cache_lock:
        entry = _cache_store.get(key)
        if not entry:
            return None
        if entry["expires_at"] <= time():
            _cache_store.pop(key, None)
            return None
        return entry["value"]


def _cache_set(key: str, value: Dict[str, Any], ttl_seconds: int) -> None:
    """Store value in cache with TTL."""
    if ttl_seconds <= 0:
        return
    with _cache_lock:
        _cache_store[key] = {"value": value, "expires_at": time() + ttl_seconds}


def _now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _standardize_response(
    answer: str,
    citations: list[str],
    metadata: Optional[Dict[str, Any]] = None,
    quality: str = "verified"
) -> Dict[str, Any]:
    """Create standardized response format."""
    response = {
        "answer": answer,
        "citations": citations,
        "retrieved_at": _now_iso(),
        "quality": quality,
    }
    if metadata:
        response["metadata"] = metadata
    return response


def _error_response(message: str, citations: list[str] = None) -> Dict[str, Any]:
    """Create standardized error response."""
    return _standardize_response(
        answer=message,
        citations=citations or [],
        quality="error"
    )


# ==================== NASA PROVIDERS ====================

@router.get("/nasa/apod")
def nasa_apod(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    api_key: str = Query("DEMO_KEY", description="NASA API key")
) -> Dict[str, Any]:
    """
    NASA Astronomy Picture of the Day.

    Args:
        date: Optional date in YYYY-MM-DD format (defaults to today)
        api_key: NASA API key (defaults to DEMO_KEY)

    Returns:
        Standardized response with APOD data
    """
    cache_key = _cache_key("nasa:apod", {"date": date})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = "https://api.nasa.gov/planetary/apod"
        params = {"api_key": api_key}
        if date:
            params["date"] = date

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        title = data.get("title", "")
        explanation = data.get("explanation", "")
        media_url = data.get("url", "")

        result = _standardize_response(
            answer=f"{title}: {explanation}",
            citations=[media_url, "https://api.nasa.gov/"],
            metadata={
                "date": data.get("date"),
                "media_type": data.get("media_type"),
                "hdurl": data.get("hdurl"),
                "copyright": data.get("copyright")
            }
        )
        _cache_set(cache_key, result, CACHE_TTL_DAILY)
        return result

    except requests.RequestException as e:
        logger.error(f"NASA APOD API error: {e}")
        return _error_response(f"Failed to fetch NASA APOD: {str(e)}")


@router.get("/nasa/mars_rover")
def nasa_mars_rover(
    rover: str = Query("curiosity", description="Rover name: curiosity, opportunity, spirit"),
    sol: int = Query(1000, description="Martian sol (day)"),
    camera: Optional[str] = Query(None, description="Camera abbreviation (e.g., FHAZ, RHAZ, MAST)"),
    api_key: str = Query("DEMO_KEY", description="NASA API key")
) -> Dict[str, Any]:
    """
    NASA Mars Rover Photos.

    Args:
        rover: Rover name (curiosity, opportunity, spirit)
        sol: Martian sol (day number)
        camera: Optional camera filter
        api_key: NASA API key

    Returns:
        Standardized response with Mars rover photos
    """
    cache_key = _cache_key("nasa:mars_rover", {"rover": rover, "sol": sol, "camera": camera})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = f"https://api.nasa.gov/mars-photos/api/v1/rovers/{rover}/photos"
        params = {"sol": sol, "api_key": api_key}
        if camera:
            params["camera"] = camera

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        photos = data.get("photos", [])
        if not photos:
            result = _error_response(
                f"No photos found for {rover} on sol {sol}",
                ["https://api.nasa.gov/"]
            )
        else:
            photo_urls = [p.get("img_src") for p in photos[:5]]  # First 5 photos
            result = _standardize_response(
                answer=f"Found {len(photos)} photos from {rover} rover on sol {sol}. First photo: {photo_urls[0] if photo_urls else 'N/A'}",
                citations=photo_urls + ["https://api.nasa.gov/"],
                metadata={
                    "rover": rover,
                    "sol": sol,
                    "total_photos": len(photos),
                    "camera": camera,
                    "earth_date": photos[0].get("earth_date") if photos else None
                }
            )

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.RequestException as e:
        logger.error(f"NASA Mars Rover API error: {e}")
        return _error_response(f"Failed to fetch Mars Rover photos: {str(e)}")


@router.get("/nasa/asteroids")
def nasa_asteroids(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    api_key: str = Query("DEMO_KEY", description="NASA API key")
) -> Dict[str, Any]:
    """
    NASA Near Earth Objects (Asteroids).

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        api_key: NASA API key

    Returns:
        Standardized response with asteroid data
    """
    # Default to today if no dates provided
    if not start_date:
        start_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not end_date:
        end_date = start_date

    cache_key = _cache_key("nasa:asteroids", {"start": start_date, "end": end_date})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = "https://api.nasa.gov/neo/rest/v1/feed"
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "api_key": api_key
        }

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        element_count = data.get("element_count", 0)
        near_earth_objects = data.get("near_earth_objects", {})

        # Collect info about asteroids
        asteroids_info = []
        for date, asteroids in near_earth_objects.items():
            for asteroid in asteroids[:3]:  # First 3 per date
                name = asteroid.get("name", "Unknown")
                is_hazardous = asteroid.get("is_potentially_hazardous_asteroid", False)
                asteroids_info.append(f"{name} ({'hazardous' if is_hazardous else 'safe'})")

        result = _standardize_response(
            answer=f"Found {element_count} near-Earth objects between {start_date} and {end_date}. Examples: {', '.join(asteroids_info[:5])}",
            citations=["https://api.nasa.gov/", "https://cneos.jpl.nasa.gov/"],
            metadata={
                "element_count": element_count,
                "start_date": start_date,
                "end_date": end_date
            }
        )
        _cache_set(cache_key, result, CACHE_TTL_DAILY)
        return result

    except requests.RequestException as e:
        logger.error(f"NASA Asteroids API error: {e}")
        return _error_response(f"Failed to fetch asteroid data: {str(e)}")


# ==================== GOVERNMENT DATA PROVIDERS ====================

@router.get("/census/demographics")
def census_demographics(
    state: str = Query("CA", description="Two-letter state code (e.g., CA)"),
    metric: str = Query("population", description="Metric to retrieve")
) -> Dict[str, Any]:
    """
    US Census Bureau demographics data.

    Args:
        state: Two-letter state code
        metric: Demographic metric to retrieve

    Returns:
        Standardized response with census data
    """
    cache_key = _cache_key("census:demographics", {"state": state, "metric": metric})
    if cached := _cache_get(cache_key):
        return cached

    try:
        # Using Census API - public endpoint
        url = "https://api.census.gov/data/2021/pep/population"
        params = {
            "get": "POP_2021,NAME",
            "for": f"state:{state}",
        }

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if len(data) > 1:
            headers = data[0]
            values = data[1]
            pop = values[0] if len(values) > 0 else "N/A"
            name = values[1] if len(values) > 1 else state

            result = _standardize_response(
                answer=f"{name} population (2021): {pop}",
                citations=["https://www.census.gov/data/developers/data-sets.html"],
                metadata={"state": state, "population": pop, "year": 2021}
            )
        else:
            result = _error_response(f"No census data found for state {state}")

        _cache_set(cache_key, result, CACHE_TTL_DAILY)
        return result

    except requests.RequestException as e:
        logger.error(f"Census API error: {e}")
        return _error_response(f"Failed to fetch census data: {str(e)}")


@router.get("/worldbank/indicators")
def worldbank_indicators(
    country: str = Query("USA", description="Country code (e.g., USA, GBR)"),
    indicator: str = Query("NY.GDP.MKTP.CD", description="Indicator code"),
    date: Optional[str] = Query(None, description="Year or year range (e.g., 2020 or 2015:2020)")
) -> Dict[str, Any]:
    """
    World Bank economic indicators.

    Args:
        country: ISO country code
        indicator: World Bank indicator code
        date: Optional year or year range

    Returns:
        Standardized response with World Bank data
    """
    cache_key = _cache_key("worldbank:indicators", {"country": country, "indicator": indicator, "date": date})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
        params = {"format": "json", "per_page": 10}
        if date:
            params["date"] = date

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if len(data) > 1 and data[1]:
            records = data[1]
            latest = records[0]
            value = latest.get("value")
            year = latest.get("date")
            country_name = latest.get("country", {}).get("value", country)
            indicator_name = latest.get("indicator", {}).get("value", indicator)

            result = _standardize_response(
                answer=f"{country_name} - {indicator_name} ({year}): {value}",
                citations=["https://data.worldbank.org/"],
                metadata={
                    "country": country,
                    "indicator": indicator,
                    "value": value,
                    "year": year
                }
            )
        else:
            result = _error_response(
                f"No World Bank data found for {country}/{indicator}",
                ["https://data.worldbank.org/"]
            )

        _cache_set(cache_key, result, CACHE_TTL_DAILY)
        return result

    except requests.RequestException as e:
        logger.error(f"World Bank API error: {e}")
        return _error_response(f"Failed to fetch World Bank data: {str(e)}")


@router.get("/fred/economic")
def fred_economic(
    series_id: str = Query("GNPCA", description="FRED series ID"),
    api_key: Optional[str] = Query(None, description="FRED API key (required)")
) -> Dict[str, Any]:
    """
    Federal Reserve Economic Data (FRED).

    Args:
        series_id: FRED series identifier
        api_key: FRED API key (required - get from https://fred.stlouisfed.org/docs/api/api_key.html)

    Returns:
        Standardized response with FRED data
    """
    if not api_key:
        return _error_response(
            "FRED API key required. Get one at https://fred.stlouisfed.org/docs/api/api_key.html",
            ["https://fred.stlouisfed.org/"]
        )

    cache_key = _cache_key("fred:economic", {"series_id": series_id})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1
        }

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        observations = data.get("observations", [])
        if observations:
            latest = observations[0]
            value = latest.get("value")
            date = latest.get("date")

            result = _standardize_response(
                answer=f"FRED series {series_id} as of {date}: {value}",
                citations=["https://fred.stlouisfed.org/"],
                metadata={"series_id": series_id, "value": value, "date": date}
            )
        else:
            result = _error_response(f"No data found for FRED series {series_id}")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.RequestException as e:
        logger.error(f"FRED API error: {e}")
        return _error_response(f"Failed to fetch FRED data: {str(e)}")


@router.get("/imf/financial")
def imf_financial(
    indicator: str = Query("NGDP_RPCH", description="IMF indicator code"),
    country: str = Query("US", description="Country code")
) -> Dict[str, Any]:
    """
    International Monetary Fund (IMF) financial statistics.

    Args:
        indicator: IMF indicator code
        country: Country code

    Returns:
        Standardized response with IMF data
    """
    cache_key = _cache_key("imf:financial", {"indicator": indicator, "country": country})
    if cached := _cache_get(cache_key):
        return cached

    try:
        # IMF JSON RESTful API
        url = f"https://www.imf.org/external/datamapper/api/v1/{indicator}"

        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        values_data = data.get("values", {}).get(indicator, {}).get(country, {})

        if values_data:
            # Get latest year
            latest_year = max(values_data.keys())
            latest_value = values_data[latest_year]

            result = _standardize_response(
                answer=f"IMF {indicator} for {country} ({latest_year}): {latest_value}",
                citations=["https://www.imf.org/"],
                metadata={
                    "indicator": indicator,
                    "country": country,
                    "year": latest_year,
                    "value": latest_value
                }
            )
        else:
            result = _error_response(f"No IMF data found for {indicator}/{country}")

        _cache_set(cache_key, result, CACHE_TTL_DAILY)
        return result

    except requests.RequestException as e:
        logger.error(f"IMF API error: {e}")
        return _error_response(f"Failed to fetch IMF data: {str(e)}")


@router.get("/eu/open_data")
def eu_open_data(
    query: str = Query(..., description="Search query")
) -> Dict[str, Any]:
    """
    European Union Open Data Portal.

    Args:
        query: Search query

    Returns:
        Standardized response with EU open data results
    """
    cache_key = _cache_key("eu:open_data", {"query": query})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = "https://data.europa.eu/api/hub/search/datasets"
        params = {"query": query, "limit": 5}

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        if results:
            titles = [r.get("title", {}).get("en", "Untitled") for r in results]
            result = _standardize_response(
                answer=f"Found {len(results)} EU datasets for '{query}': {', '.join(titles)}",
                citations=["https://data.europa.eu/"],
                metadata={"query": query, "count": len(results)}
            )
        else:
            result = _error_response(f"No EU datasets found for '{query}'")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.RequestException as e:
        logger.error(f"EU Open Data API error: {e}")
        return _error_response(f"Failed to fetch EU data: {str(e)}")


@router.get("/uk/police_data")
def uk_police_data(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    date: Optional[str] = Query(None, description="Date in YYYY-MM format")
) -> Dict[str, Any]:
    """
    UK Police crime data.

    Args:
        lat: Latitude
        lng: Longitude
        date: Optional date in YYYY-MM format

    Returns:
        Standardized response with UK crime data
    """
    cache_key = _cache_key("uk:police", {"lat": lat, "lng": lng, "date": date})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = "https://data.police.uk/api/crimes-street/all-crime"
        params = {"lat": lat, "lng": lng}
        if date:
            params["date"] = date

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if data:
            # Count by category
            categories = {}
            for crime in data:
                cat = crime.get("category", "unknown")
                categories[cat] = categories.get(cat, 0) + 1

            result = _standardize_response(
                answer=f"Found {len(data)} crimes near ({lat}, {lng}). Top categories: {dict(sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3])}",
                citations=["https://data.police.uk/"],
                metadata={"total": len(data), "categories": categories, "date": date}
            )
        else:
            result = _error_response(f"No crime data found for location ({lat}, {lng})")

        _cache_set(cache_key, result, CACHE_TTL_DAILY)
        return result

    except requests.RequestException as e:
        logger.error(f"UK Police API error: {e}")
        return _error_response(f"Failed to fetch UK police data: {str(e)}")


@router.get("/health/covid_stats")
def health_covid_stats(
    country: Optional[str] = Query(None, description="Country name (e.g., USA)")
) -> Dict[str, Any]:
    """
    COVID-19 statistics from disease.sh.

    Args:
        country: Optional country name (defaults to global stats)

    Returns:
        Standardized response with COVID-19 data
    """
    cache_key = _cache_key("covid:stats", {"country": country})
    if cached := _cache_get(cache_key):
        return cached

    try:
        if country:
            url = f"https://disease.sh/v3/covid-19/countries/{country}"
        else:
            url = "https://disease.sh/v3/covid-19/all"

        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        cases = data.get("cases", 0)
        deaths = data.get("deaths", 0)
        recovered = data.get("recovered", 0)
        updated = data.get("updated", 0)

        location = country if country else "Global"
        result = _standardize_response(
            answer=f"COVID-19 stats for {location}: {cases:,} cases, {deaths:,} deaths, {recovered:,} recovered (as of {datetime.fromtimestamp(updated/1000).strftime('%Y-%m-%d')})",
            citations=["https://disease.sh/"],
            metadata={
                "country": country,
                "cases": cases,
                "deaths": deaths,
                "recovered": recovered,
                "updated": updated
            }
        )
        _cache_set(cache_key, result, CACHE_TTL_MEDIUM)
        return result

    except requests.RequestException as e:
        logger.error(f"COVID stats API error: {e}")
        return _error_response(f"Failed to fetch COVID-19 data: {str(e)}")


@router.get("/datagov/search")
def datagov_search(
    query: str = Query(..., description="Search query")
) -> Dict[str, Any]:
    """
    Data.gov dataset search.

    Args:
        query: Search query

    Returns:
        Standardized response with data.gov results
    """
    cache_key = _cache_key("datagov:search", {"query": query})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = "https://catalog.data.gov/api/3/action/package_search"
        params = {"q": query, "rows": 5}

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if data.get("success"):
            results = data.get("result", {}).get("results", [])
            if results:
                titles = [r.get("title", "Untitled") for r in results]
                count = data.get("result", {}).get("count", 0)

                result = _standardize_response(
                    answer=f"Found {count} datasets on data.gov for '{query}'. Top results: {', '.join(titles)}",
                    citations=["https://data.gov/"],
                    metadata={"query": query, "count": count}
                )
            else:
                result = _error_response(f"No datasets found on data.gov for '{query}'")
        else:
            result = _error_response("Data.gov search failed")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.RequestException as e:
        logger.error(f"Data.gov API error: {e}")
        return _error_response(f"Failed to search data.gov: {str(e)}")


# ==================== KNOWLEDGE/RESEARCH PROVIDERS ====================

@router.get("/wikipedia")
def wikipedia_search(
    q: str = Query(..., description="Search query for Wikipedia article")
) -> Dict[str, Any]:
    """
    Wikipedia article summary search.

    Args:
        q: Search query

    Returns:
        Standardized response with Wikipedia article summary
    """
    cache_key = _cache_key("wikipedia:search", {"q": q})
    if cached := _cache_get(cache_key):
        return cached

    try:
        # Wikipedia API for article summary
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + requests.utils.quote(q)
        headers = {"User-Agent": "Axiomeer/1.0 (https://github.com/axiomeer/marketplace)"}

        response = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()

        data = response.json()

        if data.get("type") == "standard":
            title = data.get("title", "")
            extract = data.get("extract", "")
            page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")

            result = _standardize_response(
                answer=f"{title}: {extract}",
                citations=[page_url, "https://en.wikipedia.org/"],
                metadata={"title": title, "url": page_url}
            )
        else:
            result = _error_response(f"No Wikipedia article found for '{q}'")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return _error_response(f"No Wikipedia article found for '{q}'")
        logger.error(f"Wikipedia API error: {e}")
        return _error_response(f"Failed to search Wikipedia: {str(e)}")
    except Exception as e:
        logger.error(f"Wikipedia search error: {e}")
        return _error_response(f"Failed to search Wikipedia: {str(e)}")


@router.get("/arxiv/papers")
def arxiv_papers(
    search_query: Optional[str] = Query(None, description="Search query"),
    query: Optional[str] = Query(None, description="Alias for search_query"),
    max_results: int = Query(5, description="Maximum results to return")
) -> Dict[str, Any]:
    """
    arXiv research papers search.

    Args:
        search_query: Search query (preferred parameter name)
        query: Alias for search_query
        max_results: Maximum number of results

    Returns:
        Standardized response with arXiv papers
    """
    # Accept either parameter name
    q = search_query or query
    if not q:
        return _error_response("No search query provided")

    cache_key = _cache_key("arxiv:papers", {"query": q, "max_results": max_results})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{q}",
            "start": 0,
            "max_results": max_results
        }

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()

        # Parse XML response
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)

        # Extract entries
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)

        if entries:
            papers = []
            for entry in entries[:max_results]:
                title = entry.find("atom:title", ns)
                link = entry.find("atom:id", ns)
                papers.append({
                    "title": title.text.strip() if title is not None else "N/A",
                    "url": link.text.strip() if link is not None else "N/A"
                })

            titles = [p["title"] for p in papers]
            urls = [p["url"] for p in papers]

            result = _standardize_response(
                answer=f"Found {len(papers)} arXiv papers for '{q}': {'; '.join(titles[:3])}",
                citations=urls + ["https://arxiv.org/"],
                metadata={"query": q, "count": len(papers)}
            )
        else:
            result = _error_response(f"No arXiv papers found for '{q}'")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except Exception as e:
        logger.error(f"arXiv API error: {e}")
        return _error_response(f"Failed to search arXiv: {str(e)}")


@router.get("/pubmed/search")
def pubmed_search(
    term: Optional[str] = Query(None, description="Search term"),
    query: Optional[str] = Query(None, description="Alias for term"),
    max_results: int = Query(5, description="Maximum results")
) -> Dict[str, Any]:
    """
    PubMed biomedical literature search.

    Args:
        term: Search term (preferred parameter name)
        query: Alias for term
        max_results: Maximum results to return

    Returns:
        Standardized response with PubMed articles
    """
    # Accept either parameter
    search_term = term or query
    if not search_term:
        return _error_response("No search term provided")

    cache_key = _cache_key("pubmed:search", {"query": search_term, "max_results": max_results})
    if cached := _cache_get(cache_key):
        return cached

    try:
        # Search for IDs
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": search_term,
            "retmax": max_results,
            "retmode": "json"
        }

        response = requests.get(search_url, params=search_params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        id_list = data.get("esearchresult", {}).get("idlist", [])

        if id_list:
            # Fetch summaries
            summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            summary_params = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "json"
            }

            summary_response = requests.get(summary_url, params=summary_params, timeout=DEFAULT_TIMEOUT)
            summary_response.raise_for_status()
            summary_data = summary_response.json()

            results = summary_data.get("result", {})
            titles = []
            citations = []

            for pmid in id_list:
                if pmid in results:
                    article = results[pmid]
                    title = article.get("title", "N/A")
                    titles.append(title)
                    citations.append(f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/")

            result = _standardize_response(
                answer=f"Found {len(titles)} PubMed articles for '{search_term}': {'; '.join(titles[:3])}",
                citations=citations[:5],
                metadata={"query": search_term, "count": len(titles)}
            )
        else:
            result = _error_response(f"No PubMed articles found for '{search_term}'")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.RequestException as e:
        logger.error(f"PubMed API error: {e}")
        return _error_response(f"Failed to search PubMed: {str(e)}")


@router.get("/semantic_scholar/papers")
def semantic_scholar_papers(
    query: str = Query(..., description="Search query"),
    limit: int = Query(5, description="Maximum results")
) -> Dict[str, Any]:
    """
    Semantic Scholar paper search.

    Args:
        query: Search query
        limit: Maximum results

    Returns:
        Standardized response with Semantic Scholar papers
    """
    cache_key = _cache_key("semantic_scholar:papers", {"query": query, "limit": limit})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,authors,year,citationCount,url"
        }

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        papers = data.get("data", [])
        if papers:
            titles = []
            citations = []

            for paper in papers:
                title = paper.get("title", "N/A")
                year = paper.get("year", "N/A")
                citation_count = paper.get("citationCount", 0)
                titles.append(f"{title} ({year}, {citation_count} citations)")

                paper_url = paper.get("url")
                if paper_url:
                    citations.append(paper_url)

            result = _standardize_response(
                answer=f"Found {len(papers)} papers on Semantic Scholar for '{query}': {'; '.join(titles[:3])}",
                citations=citations + ["https://www.semanticscholar.org/"],
                metadata={"query": query, "count": len(papers)}
            )
        else:
            result = _error_response(f"No papers found on Semantic Scholar for '{query}'")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.RequestException as e:
        logger.error(f"Semantic Scholar API error: {e}")
        return _error_response(f"Failed to search Semantic Scholar: {str(e)}")


@router.get("/crossref/metadata")
def crossref_metadata(
    doi: Optional[str] = Query(None, description="DOI to lookup"),
    query: Optional[str] = Query(None, description="Search query")
) -> Dict[str, Any]:
    """
    Crossref metadata for scholarly works.

    Args:
        doi: DOI to lookup
        query: Search query (if no DOI provided)

    Returns:
        Standardized response with Crossref metadata
    """
    if not doi and not query:
        return _error_response("Either 'doi' or 'query' parameter is required")

    cache_key = _cache_key("crossref:metadata", {"doi": doi, "query": query})
    if cached := _cache_get(cache_key):
        return cached

    try:
        if doi:
            url = f"https://api.crossref.org/works/{doi}"
            response = requests.get(url, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            message = data.get("message", {})
            title = message.get("title", ["N/A"])[0]
            authors = message.get("author", [])
            author_names = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors[:3]]

            result = _standardize_response(
                answer=f"DOI {doi}: {title}. Authors: {', '.join(author_names)}",
                citations=[f"https://doi.org/{doi}"],
                metadata={"doi": doi, "title": title}
            )
        else:
            url = "https://api.crossref.org/works"
            params = {"query": query, "rows": 5}
            response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            items = data.get("message", {}).get("items", [])
            if items:
                titles = [item.get("title", ["N/A"])[0] for item in items]
                dois = [item.get("DOI") for item in items if item.get("DOI")]

                result = _standardize_response(
                    answer=f"Found {len(items)} works on Crossref for '{query}': {'; '.join(titles[:3])}",
                    citations=[f"https://doi.org/{d}" for d in dois[:3]],
                    metadata={"query": query, "count": len(items)}
                )
            else:
                result = _error_response(f"No works found on Crossref for '{query}'")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.RequestException as e:
        logger.error(f"Crossref API error: {e}")
        return _error_response(f"Failed to fetch Crossref data: {str(e)}")


@router.get("/wikidata/sparql")
def wikidata_sparql(
    query: str = Query(..., description="SPARQL query")
) -> Dict[str, Any]:
    """
    Wikidata SPARQL query endpoint.

    Args:
        query: SPARQL query

    Returns:
        Standardized response with Wikidata results
    """
    cache_key = _cache_key("wikidata:sparql", {"query": query})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = "https://query.wikidata.org/sparql"
        headers = {"Accept": "application/json"}
        params = {"query": query}

        response = requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", {}).get("bindings", [])
        if results:
            # Extract first few results
            result_texts = []
            for r in results[:5]:
                values = [v.get("value") for v in r.values()]
                result_texts.append(" | ".join(str(v) for v in values))

            result = _standardize_response(
                answer=f"Wikidata query returned {len(results)} results. Sample: {'; '.join(result_texts[:3])}",
                citations=["https://www.wikidata.org/"],
                metadata={"query": query, "count": len(results)}
            )
        else:
            result = _error_response("Wikidata query returned no results")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.RequestException as e:
        logger.error(f"Wikidata SPARQL API error: {e}")
        return _error_response(f"Failed to query Wikidata: {str(e)}")


@router.get("/dbpedia/sparql")
def dbpedia_sparql(
    query: str = Query(..., description="SPARQL query")
) -> Dict[str, Any]:
    """
    DBpedia SPARQL query endpoint.

    Args:
        query: SPARQL query

    Returns:
        Standardized response with DBpedia results
    """
    cache_key = _cache_key("dbpedia:sparql", {"query": query})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = "https://dbpedia.org/sparql"
        headers = {"Accept": "application/json"}
        params = {"query": query, "format": "json"}

        response = requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", {}).get("bindings", [])
        if results:
            result_texts = []
            for r in results[:5]:
                values = [v.get("value") for v in r.values()]
                result_texts.append(" | ".join(str(v) for v in values))

            result = _standardize_response(
                answer=f"DBpedia query returned {len(results)} results. Sample: {'; '.join(result_texts[:3])}",
                citations=["https://dbpedia.org/"],
                metadata={"query": query, "count": len(results)}
            )
        else:
            result = _error_response("DBpedia query returned no results")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.RequestException as e:
        logger.error(f"DBpedia SPARQL API error: {e}")
        return _error_response(f"Failed to query DBpedia: {str(e)}")


@router.get("/archive_org/search")
def archive_org_search(
    query: str = Query(..., description="Search query"),
    media_type: Optional[str] = Query(None, description="Media type filter (e.g., texts, audio, movies)")
) -> Dict[str, Any]:
    """
    Internet Archive search.

    Args:
        query: Search query
        media_type: Optional media type filter

    Returns:
        Standardized response with Internet Archive results
    """
    cache_key = _cache_key("archive_org:search", {"query": query, "media_type": media_type})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = "https://archive.org/advancedsearch.php"
        search_query = query
        if media_type:
            search_query = f"{query} AND mediatype:{media_type}"

        params = {
            "q": search_query,
            "output": "json",
            "rows": 5
        }

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        docs = data.get("response", {}).get("docs", [])
        if docs:
            titles = []
            citations = []

            for doc in docs:
                title = doc.get("title", "N/A")
                identifier = doc.get("identifier", "")
                titles.append(title)
                if identifier:
                    citations.append(f"https://archive.org/details/{identifier}")

            result = _standardize_response(
                answer=f"Found {len(docs)} items on Internet Archive for '{query}': {'; '.join(titles[:3])}",
                citations=citations,
                metadata={"query": query, "media_type": media_type, "count": len(docs)}
            )
        else:
            result = _error_response(f"No items found on Internet Archive for '{query}'")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.RequestException as e:
        logger.error(f"Internet Archive API error: {e}")
        return _error_response(f"Failed to search Internet Archive: {str(e)}")


@router.get("/gutenberg/books")
def gutenberg_books(
    query: Optional[str] = Query(None, description="Search query for books"),
    author: Optional[str] = Query(None, description="Author name to search")
) -> Dict[str, Any]:
    """
    Project Gutenberg book search.

    Args:
        query: Search query for books
        author: Author name (alias for query)

    Returns:
        Standardized response with Gutenberg books
    """
    # Accept either parameter
    search_term = query or author
    if not search_term:
        return _error_response("No search query or author provided")

    cache_key = _cache_key("gutenberg:books", {"query": search_term})
    if cached := _cache_get(cache_key):
        return cached

    try:
        # Using Gutendex API
        url = "https://gutendex.com/books"
        params = {"search": search_term}

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        books = data.get("results", [])
        if books:
            titles = []
            citations = []

            for book in books[:5]:
                title = book.get("title", "N/A")
                authors = book.get("authors", [])
                author_names = ", ".join([a.get("name", "Unknown") for a in authors])
                titles.append(f"{title} by {author_names}")

                # Get text URL
                formats = book.get("formats", {})
                text_url = formats.get("text/html") or formats.get("text/plain; charset=utf-8")
                if text_url:
                    citations.append(text_url)

            result = _standardize_response(
                answer=f"Found {len(books)} books on Project Gutenberg for '{query}': {'; '.join(titles[:3])}",
                citations=citations + ["https://www.gutenberg.org/"],
                metadata={"query": query, "count": len(books)}
            )
        else:
            result = _error_response(f"No books found on Project Gutenberg for '{query}'")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.RequestException as e:
        logger.error(f"Project Gutenberg API error: {e}")
        return _error_response(f"Failed to search Project Gutenberg: {str(e)}")


# ==================== FINANCIAL/CRYPTO PROVIDERS ====================

@router.get("/coingecko/crypto")
def coingecko_crypto(
    coin_id: str = Query(..., description="Coin ID (e.g., bitcoin, ethereum, ripple for XRP)"),
    vs_currency: str = Query(default="usd", description="Target currency")
) -> Dict[str, Any]:
    """
    CoinGecko cryptocurrency prices.

    Args:
        coin_id: Coin identifier
        vs_currency: Target currency

    Returns:
        Standardized response with crypto price data
    """
    cache_key = _cache_key("coingecko:crypto", {"coin_id": coin_id, "vs_currency": vs_currency})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = f"https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": coin_id,
            "vs_currencies": vs_currency,
            "include_24hr_change": "true",
            "include_market_cap": "true"
        }

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if coin_id in data:
            coin_data = data[coin_id]
            price = coin_data.get(vs_currency, 0)
            change_24h = coin_data.get(f"{vs_currency}_24h_change", 0)
            market_cap = coin_data.get(f"{vs_currency}_market_cap", 0)

            result = _standardize_response(
                answer=f"{coin_id.capitalize()}: {price:,.2f} {vs_currency.upper()} (24h change: {change_24h:+.2f}%, market cap: {market_cap:,.0f})",
                citations=["https://www.coingecko.com/"],
                metadata={
                    "coin_id": coin_id,
                    "price": price,
                    "change_24h": change_24h,
                    "market_cap": market_cap,
                    "currency": vs_currency
                }
            )
        else:
            result = _error_response(f"Coin '{coin_id}' not found on CoinGecko")

        _cache_set(cache_key, result, CACHE_TTL_SHORT)
        return result

    except requests.RequestException as e:
        logger.error(f"CoinGecko API error: {e}")
        return _error_response(f"Failed to fetch CoinGecko data: {str(e)}")


@router.get("/coinbase/prices")
def coinbase_prices(
    currency_pair: str = Query(..., description="Currency pair (e.g., BTC-USD, XRP-USD, ETH-EUR)")
) -> Dict[str, Any]:
    """
    Coinbase exchange rates.

    Args:
        currency_pair: Currency pair

    Returns:
        Standardized response with Coinbase rates
    """
    cache_key = _cache_key("coinbase:prices", {"currency_pair": currency_pair})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = f"https://api.coinbase.com/v2/prices/{currency_pair}/spot"

        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        price_data = data.get("data", {})
        amount = price_data.get("amount", "N/A")
        currency = price_data.get("currency", "USD")

        result = _standardize_response(
            answer=f"{currency_pair} spot price: {amount} {currency}",
            citations=["https://www.coinbase.com/"],
            metadata={"currency_pair": currency_pair, "amount": amount, "currency": currency}
        )
        _cache_set(cache_key, result, CACHE_TTL_SHORT)
        return result

    except requests.RequestException as e:
        logger.error(f"Coinbase API error: {e}")
        return _error_response(f"Failed to fetch Coinbase data: {str(e)}")


@router.get("/blockchain/info")
def blockchain_info(
    endpoint: str = Query("stats", description="Endpoint: stats, pools, etc.")
) -> Dict[str, Any]:
    """
    Blockchain.com Bitcoin data.

    Args:
        endpoint: API endpoint (stats, pools, etc.)

    Returns:
        Standardized response with blockchain data
    """
    cache_key = _cache_key("blockchain:info", {"endpoint": endpoint})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = f"https://blockchain.info/{endpoint}"
        params = {"format": "json"}

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if endpoint == "stats":
            market_price = data.get("market_price_usd", 0)
            hash_rate = data.get("hash_rate", 0)
            difficulty = data.get("difficulty", 0)

            result = _standardize_response(
                answer=f"Bitcoin stats: Market price ${market_price:,.2f}, Hash rate {hash_rate:.2e}, Difficulty {difficulty:,.0f}",
                citations=["https://www.blockchain.com/"],
                metadata=data
            )
        else:
            result = _standardize_response(
                answer=f"Blockchain.com {endpoint} data retrieved successfully",
                citations=["https://www.blockchain.com/"],
                metadata=data
            )

        _cache_set(cache_key, result, CACHE_TTL_SHORT)
        return result

    except requests.RequestException as e:
        logger.error(f"Blockchain.com API error: {e}")
        return _error_response(f"Failed to fetch blockchain data: {str(e)}")


# ==================== GEOGRAPHIC PROVIDERS ====================

@router.get("/nominatim/geocoding")
def nominatim_geocoding(
    q: str = Query(..., description="Location query"),
    limit: int = Query(5, description="Maximum results")
) -> Dict[str, Any]:
    """
    OpenStreetMap Nominatim geocoding.

    Args:
        q: Location search query
        limit: Maximum results

    Returns:
        Standardized response with geocoding results
    """
    cache_key = _cache_key("nominatim:geocoding", {"query": q, "limit": limit})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": q,
            "format": "json",
            "limit": limit
        }
        headers = {"User-Agent": "AIMarketplace/1.0"}

        response = requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if data:
            locations = []
            for item in data:
                display_name = item.get("display_name", "N/A")
                lat = item.get("lat", "N/A")
                lon = item.get("lon", "N/A")
                locations.append(f"{display_name} ({lat}, {lon})")

            result = _standardize_response(
                answer=f"Found {len(data)} locations for '{q}': {'; '.join(locations[:3])}",
                citations=["https://www.openstreetmap.org/"],
                metadata={"query": q, "count": len(data), "results": data[:3]}
            )
        else:
            result = _error_response(f"No locations found for '{q}'")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.RequestException as e:
        logger.error(f"Nominatim API error: {e}")
        return _error_response(f"Failed to geocode with Nominatim: {str(e)}")


@router.get("/geonames/search")
def geonames_search(
    q: str = Query(..., description="Place name query"),
    username: str = Query("demo", description="GeoNames username")
) -> Dict[str, Any]:
    """
    GeoNames geographic database search.

    Args:
        q: Place name search query
        username: GeoNames username (get free at geonames.org)

    Returns:
        Standardized response with GeoNames results
    """
    cache_key = _cache_key("geonames:search", {"query": q})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = "http://api.geonames.org/searchJSON"
        params = {
            "q": q,
            "maxRows": 5,
            "username": username
        }

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        geonames = data.get("geonames", [])
        if geonames:
            places = []
            for place in geonames:
                name = place.get("name", "N/A")
                country = place.get("countryName", "N/A")
                lat = place.get("lat", "N/A")
                lng = place.get("lng", "N/A")
                population = place.get("population", 0)
                places.append(f"{name}, {country} ({lat}, {lng}, pop: {population:,})")

            result = _standardize_response(
                answer=f"Found {len(geonames)} places for '{q}': {'; '.join(places[:3])}",
                citations=["https://www.geonames.org/"],
                metadata={"query": q, "count": len(geonames)}
            )
        else:
            result = _error_response(f"No places found on GeoNames for '{q}'")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.RequestException as e:
        logger.error(f"GeoNames API error: {e}")
        return _error_response(f"Failed to search GeoNames: {str(e)}")


@router.get("/ip/geolocation")
def ip_geolocation(
    ip: Optional[str] = Query(None, description="IP address (defaults to caller's IP)")
) -> Dict[str, Any]:
    """
    IP geolocation lookup.

    Args:
        ip: Optional IP address (defaults to caller)

    Returns:
        Standardized response with geolocation data
    """
    cache_key = _cache_key("ip:geolocation", {"ip": ip or "self"})
    if cached := _cache_get(cache_key):
        return cached

    try:
        # Using ip-api.com (free for non-commercial)
        if ip:
            url = f"http://ip-api.com/json/{ip}"
        else:
            url = "http://ip-api.com/json/"

        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success":
            city = data.get("city", "N/A")
            region = data.get("regionName", "N/A")
            country = data.get("country", "N/A")
            lat = data.get("lat", "N/A")
            lon = data.get("lon", "N/A")
            isp = data.get("isp", "N/A")

            result = _standardize_response(
                answer=f"IP {data.get('query', ip or 'caller')}: {city}, {region}, {country} ({lat}, {lon}). ISP: {isp}",
                citations=["http://ip-api.com/"],
                metadata=data
            )
        else:
            result = _error_response(f"Failed to geolocate IP: {data.get('message', 'Unknown error')}")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.RequestException as e:
        logger.error(f"IP geolocation API error: {e}")
        return _error_response(f"Failed to geolocate IP: {str(e)}")


# ==================== MEDIA PROVIDERS ====================

@router.get("/omdb/movies")
def omdb_movies(
    title: Optional[str] = Query(None, description="Movie title"),
    imdb_id: Optional[str] = Query(None, description="IMDb ID"),
    api_key: Optional[str] = Query(None, description="OMDB API key (required)")
) -> Dict[str, Any]:
    """
    OMDB (Open Movie Database) movie information.

    Args:
        title: Movie title
        imdb_id: IMDb ID (alternative to title)
        api_key: OMDB API key (get free at omdbapi.com)

    Returns:
        Standardized response with movie data
    """
    if not api_key:
        return _error_response(
            "OMDB API key required. Get one at http://www.omdbapi.com/apikey.aspx",
            ["http://www.omdbapi.com/"]
        )

    if not title and not imdb_id:
        return _error_response("Either 'title' or 'imdb_id' parameter is required")

    cache_key = _cache_key("omdb:movies", {"title": title, "imdb_id": imdb_id})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = "http://www.omdbapi.com/"
        params = {"apikey": api_key}

        if imdb_id:
            params["i"] = imdb_id
        else:
            params["t"] = title

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if data.get("Response") == "True":
            movie_title = data.get("Title", "N/A")
            year = data.get("Year", "N/A")
            rating = data.get("imdbRating", "N/A")
            plot = data.get("Plot", "N/A")

            result = _standardize_response(
                answer=f"{movie_title} ({year}): {plot}. IMDb Rating: {rating}",
                citations=[f"https://www.imdb.com/title/{data.get('imdbID', '')}/"],
                metadata={
                    "title": movie_title,
                    "year": year,
                    "rating": rating,
                    "genre": data.get("Genre"),
                    "director": data.get("Director")
                }
            )
        else:
            result = _error_response(f"Movie not found: {data.get('Error', 'Unknown error')}")

        _cache_set(cache_key, result, CACHE_TTL_DAILY)
        return result

    except requests.RequestException as e:
        logger.error(f"OMDB API error: {e}")
        return _error_response(f"Failed to fetch OMDB data: {str(e)}")


@router.get("/tmdb/movies")
def tmdb_movies(
    query: Optional[str] = Query(None, description="Movie search query"),
    movie_id: Optional[int] = Query(None, description="TMDB movie ID"),
    api_key: Optional[str] = Query(None, description="TMDB API key (required)")
) -> Dict[str, Any]:
    """
    The Movie Database (TMDB) movie information.

    Args:
        query: Movie search query
        movie_id: TMDB movie ID (alternative to query)
        api_key: TMDB API key (get free at themoviedb.org)

    Returns:
        Standardized response with TMDB movie data
    """
    if not api_key:
        return _error_response(
            "TMDB API key required. Get one at https://www.themoviedb.org/settings/api",
            ["https://www.themoviedb.org/"]
        )

    if not query and not movie_id:
        return _error_response("Either 'query' or 'movie_id' parameter is required")

    cache_key = _cache_key("tmdb:movies", {"query": query, "movie_id": movie_id})
    if cached := _cache_get(cache_key):
        return cached

    try:
        if movie_id:
            url = f"https://api.themoviedb.org/3/movie/{movie_id}"
            params = {"api_key": api_key}

            response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            title = data.get("title", "N/A")
            overview = data.get("overview", "N/A")
            rating = data.get("vote_average", "N/A")
            release_date = data.get("release_date", "N/A")

            result = _standardize_response(
                answer=f"{title} ({release_date}): {overview}. Rating: {rating}/10",
                citations=[f"https://www.themoviedb.org/movie/{movie_id}"],
                metadata={
                    "title": title,
                    "rating": rating,
                    "release_date": release_date
                }
            )
        else:
            url = "https://api.themoviedb.org/3/search/movie"
            params = {"api_key": api_key, "query": query}

            response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if results:
                movies = []
                for movie in results[:5]:
                    title = movie.get("title", "N/A")
                    year = movie.get("release_date", "N/A")[:4]
                    movies.append(f"{title} ({year})")

                result = _standardize_response(
                    answer=f"Found {len(results)} movies for '{query}': {', '.join(movies[:3])}",
                    citations=["https://www.themoviedb.org/"],
                    metadata={"query": query, "count": len(results)}
                )
            else:
                result = _error_response(f"No movies found for '{query}' on TMDB")

        _cache_set(cache_key, result, CACHE_TTL_DAILY)
        return result

    except requests.RequestException as e:
        logger.error(f"TMDB API error: {e}")
        return _error_response(f"Failed to fetch TMDB data: {str(e)}")


@router.get("/musicbrainz/search")
def musicbrainz_search(
    query: str = Query(..., description="Artist or recording search query"),
    entity: str = Query("artist", description="Entity type: artist, recording, release")
) -> Dict[str, Any]:
    """
    MusicBrainz music metadata search.

    Args:
        query: Search query
        entity: Entity type (artist, recording, release)

    Returns:
        Standardized response with MusicBrainz results
    """
    cache_key = _cache_key("musicbrainz:search", {"query": query, "entity": entity})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = f"https://musicbrainz.org/ws/2/{entity}"
        params = {"query": query, "fmt": "json", "limit": 5}
        headers = {"User-Agent": "AIMarketplace/1.0"}

        response = requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        results = data.get(f"{entity}s", [])
        if results:
            items = []
            for item in results:
                if entity == "artist":
                    name = item.get("name", "N/A")
                    country = item.get("country", "N/A")
                    items.append(f"{name} ({country})")
                elif entity == "recording":
                    title = item.get("title", "N/A")
                    items.append(title)
                elif entity == "release":
                    title = item.get("title", "N/A")
                    date = item.get("date", "N/A")
                    items.append(f"{title} ({date})")

            result = _standardize_response(
                answer=f"Found {len(results)} {entity}s for '{query}': {'; '.join(items[:3])}",
                citations=["https://musicbrainz.org/"],
                metadata={"query": query, "entity": entity, "count": len(results)}
            )
        else:
            result = _error_response(f"No {entity}s found for '{query}' on MusicBrainz")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.RequestException as e:
        logger.error(f"MusicBrainz API error: {e}")
        return _error_response(f"Failed to search MusicBrainz: {str(e)}")


@router.get("/genius/lyrics")
def genius_lyrics(
    query: str = Query(..., description="Song or artist search query"),
    api_key: Optional[str] = Query(None, description="Genius API key (required)")
) -> Dict[str, Any]:
    """
    Genius lyrics and song metadata.

    Args:
        query: Song or artist search query
        api_key: Genius API key (get at genius.com/api-clients)

    Returns:
        Standardized response with Genius results
    """
    if not api_key:
        return _error_response(
            "Genius API key required. Get one at https://genius.com/api-clients",
            ["https://genius.com/"]
        )

    cache_key = _cache_key("genius:lyrics", {"query": query})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = "https://api.genius.com/search"
        params = {"q": query}
        headers = {"Authorization": f"Bearer {api_key}"}

        response = requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        hits = data.get("response", {}).get("hits", [])
        if hits:
            songs = []
            citations = []

            for hit in hits[:5]:
                result_data = hit.get("result", {})
                title = result_data.get("title", "N/A")
                artist = result_data.get("primary_artist", {}).get("name", "N/A")
                url = result_data.get("url", "")

                songs.append(f"{title} by {artist}")
                if url:
                    citations.append(url)

            result = _standardize_response(
                answer=f"Found {len(hits)} songs on Genius for '{query}': {'; '.join(songs[:3])}",
                citations=citations[:3],
                metadata={"query": query, "count": len(hits)}
            )
        else:
            result = _error_response(f"No songs found on Genius for '{query}'")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.RequestException as e:
        logger.error(f"Genius API error: {e}")
        return _error_response(f"Failed to search Genius: {str(e)}")


@router.get("/unsplash/photos")
def unsplash_photos(
    query: str = Query(..., description="Photo search query"),
    api_key: Optional[str] = Query(None, description="Unsplash API key (required)")
) -> Dict[str, Any]:
    """
    Unsplash photo search.

    Args:
        query: Photo search query
        api_key: Unsplash API key (get at unsplash.com/developers)

    Returns:
        Standardized response with Unsplash photos
    """
    if not api_key:
        return _error_response(
            "Unsplash API key required. Get one at https://unsplash.com/developers",
            ["https://unsplash.com/"]
        )

    cache_key = _cache_key("unsplash:photos", {"query": query})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = "https://api.unsplash.com/search/photos"
        params = {"query": query, "per_page": 5}
        headers = {"Authorization": f"Client-ID {api_key}"}

        response = requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        if results:
            photo_urls = []
            for photo in results:
                url = photo.get("urls", {}).get("regular", "")
                if url:
                    photo_urls.append(url)

            result = _standardize_response(
                answer=f"Found {len(results)} photos on Unsplash for '{query}'. First photo: {photo_urls[0] if photo_urls else 'N/A'}",
                citations=photo_urls,
                metadata={"query": query, "count": len(results)}
            )
        else:
            result = _error_response(f"No photos found on Unsplash for '{query}'")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.RequestException as e:
        logger.error(f"Unsplash API error: {e}")
        return _error_response(f"Failed to search Unsplash: {str(e)}")


@router.get("/pexels/media")
def pexels_media(
    query: str = Query(..., description="Media search query"),
    media_type: str = Query("photos", description="Media type: photos or videos"),
    api_key: Optional[str] = Query(None, description="Pexels API key (required)")
) -> Dict[str, Any]:
    """
    Pexels photos and videos search.

    Args:
        query: Media search query
        media_type: Type of media (photos or videos)
        api_key: Pexels API key (get at pexels.com/api)

    Returns:
        Standardized response with Pexels media
    """
    if not api_key:
        return _error_response(
            "Pexels API key required. Get one at https://www.pexels.com/api/",
            ["https://www.pexels.com/"]
        )

    cache_key = _cache_key("pexels:media", {"query": query, "media_type": media_type})
    if cached := _cache_get(cache_key):
        return cached

    try:
        if media_type == "videos":
            url = "https://api.pexels.com/videos/search"
        else:
            url = "https://api.pexels.com/v1/search"

        params = {"query": query, "per_page": 5}
        headers = {"Authorization": api_key}

        response = requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        results = data.get(media_type, [])
        if results:
            media_urls = []
            for item in results:
                if media_type == "videos":
                    video_files = item.get("video_files", [])
                    if video_files:
                        media_urls.append(video_files[0].get("link", ""))
                else:
                    media_urls.append(item.get("src", {}).get("large", ""))

            result = _standardize_response(
                answer=f"Found {len(results)} {media_type} on Pexels for '{query}'. First item: {media_urls[0] if media_urls else 'N/A'}",
                citations=[url for url in media_urls if url],
                metadata={"query": query, "media_type": media_type, "count": len(results)}
            )
        else:
            result = _error_response(f"No {media_type} found on Pexels for '{query}'")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.RequestException as e:
        logger.error(f"Pexels API error: {e}")
        return _error_response(f"Failed to search Pexels: {str(e)}")


# ==================== LANGUAGE PROVIDERS ====================

@router.get("/datamuse/words")
def datamuse_words(
    query: str = Query("happy", description="Word query"),
    query_type: str = Query("ml", description="Query type: ml (means like), sl (sounds like), rel_* (related)")
) -> Dict[str, Any]:
    """
    Datamuse word-finding API.

    Args:
        query: Word query
        query_type: Type of query (ml, sl, rel_syn, etc.)

    Returns:
        Standardized response with word results
    """
    cache_key = _cache_key("datamuse:words", {"query": query, "query_type": query_type})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = "https://api.datamuse.com/words"
        params = {query_type: query, "max": 10}

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if data:
            words = [item.get("word", "") for item in data]
            result = _standardize_response(
                answer=f"Words {query_type} '{query}': {', '.join(words[:10])}",
                citations=["https://www.datamuse.com/api/"],
                metadata={"query": query, "query_type": query_type, "count": len(words)}
            )
        else:
            result = _error_response(f"No words found for '{query}' with query type '{query_type}'")

        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except requests.RequestException as e:
        logger.error(f"Datamuse API error: {e}")
        return _error_response(f"Failed to search Datamuse: {str(e)}")


# ==================== UTILITIES PROVIDERS ====================

@router.get("/random/user")
def random_user(
    results: int = Query(1, description="Number of users to generate"),
    nationality: Optional[str] = Query(None, description="Nationality code (e.g., US, GB)")
) -> Dict[str, Any]:
    """
    Random user data generator.

    Args:
        results: Number of users to generate
        nationality: Optional nationality filter

    Returns:
        Standardized response with random user data
    """
    cache_key = _cache_key("random:user", {"results": results, "nationality": nationality, "time": int(time())})

    try:
        url = "https://randomuser.me/api/"
        params = {"results": results}
        if nationality:
            params["nat"] = nationality

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        users = data.get("results", [])
        if users:
            user_info = []
            for user in users:
                name = user.get("name", {})
                full_name = f"{name.get('first', '')} {name.get('last', '')}".strip()
                email = user.get("email", "")
                user_info.append(f"{full_name} ({email})")

            result = _standardize_response(
                answer=f"Generated {len(users)} random user(s): {'; '.join(user_info)}",
                citations=["https://randomuser.me/"],
                metadata={"count": len(users), "users": users}
            )
        else:
            result = _error_response("Failed to generate random users")

        return result

    except requests.RequestException as e:
        logger.error(f"Random User API error: {e}")
        return _error_response(f"Failed to generate random users: {str(e)}")


@router.get("/random/data")
def random_data(
    data_type: str = Query("number", description="Data type: number, string, uuid, boolean")
) -> Dict[str, Any]:
    """
    Random data generator using UUID API.

    Args:
        data_type: Type of random data to generate

    Returns:
        Standardized response with random data
    """
    try:
        import uuid
        import random
        import string

        if data_type == "uuid":
            data = str(uuid.uuid4())
        elif data_type == "number":
            data = random.randint(1, 1000000)
        elif data_type == "string":
            data = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        elif data_type == "boolean":
            data = random.choice([True, False])
        else:
            return _error_response(f"Unsupported data type: {data_type}")

        result = _standardize_response(
            answer=f"Generated random {data_type}: {data}",
            citations=[],
            metadata={"data_type": data_type, "value": data}
        )
        return result

    except Exception as e:
        logger.error(f"Random data generation error: {e}")
        return _error_response(f"Failed to generate random data: {str(e)}")


@router.get("/qr/generator")
def qr_generator(
    data: str = Query("Hello World", description="Data to encode in QR code"),
    size: str = Query("200x200", description="QR code size (e.g., 200x200)")
) -> Dict[str, Any]:
    """
    QR code generator.

    Args:
        data: Data to encode
        size: QR code size

    Returns:
        Standardized response with QR code URL
    """
    cache_key = _cache_key("qr:generator", {"data": data, "size": size})
    if cached := _cache_get(cache_key):
        return cached

    try:
        # Using qrcode API
        from urllib.parse import quote
        encoded_data = quote(data)
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size={size}&data={encoded_data}"

        result = _standardize_response(
            answer=f"QR code generated for: {data}",
            citations=[qr_url],
            metadata={"data": data, "size": size, "qr_url": qr_url}
        )
        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result

    except Exception as e:
        logger.error(f"QR code generation error: {e}")
        return _error_response(f"Failed to generate QR code: {str(e)}")


@router.get("/placeholder/images")
def placeholder_images(
    width: int = Query(400, description="Image width"),
    height: int = Query(300, description="Image height")
) -> Dict[str, Any]:
    """
    Lorem Picsum placeholder images.

    Args:
        width: Image width
        height: Image height

    Returns:
        Standardized response with placeholder image URL
    """
    try:
        image_url = f"https://picsum.photos/{width}/{height}"

        result = _standardize_response(
            answer=f"Placeholder image ({width}x{height}): {image_url}",
            citations=[image_url, "https://picsum.photos/"],
            metadata={"width": width, "height": height, "url": image_url}
        )
        return result

    except Exception as e:
        logger.error(f"Placeholder image error: {e}")
        return _error_response(f"Failed to generate placeholder image: {str(e)}")


@router.get("/joke/api")
def joke_api(
    category: Optional[str] = Query(None, description="Joke category")
) -> Dict[str, Any]:
    """
    JokeAPI random jokes.

    Args:
        category: Optional joke category

    Returns:
        Standardized response with a joke
    """
    try:
        url = "https://v2.jokeapi.dev/joke/Any"
        if category:
            url = f"https://v2.jokeapi.dev/joke/{category}"

        params = {"safe-mode": ""}  # Safe mode enabled

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if data.get("type") == "single":
            joke = data.get("joke", "")
        else:
            setup = data.get("setup", "")
            delivery = data.get("delivery", "")
            joke = f"{setup} {delivery}"

        result = _standardize_response(
            answer=f"Joke: {joke}",
            citations=["https://jokeapi.dev/"],
            metadata={"category": data.get("category"), "type": data.get("type")}
        )
        return result

    except requests.RequestException as e:
        logger.error(f"JokeAPI error: {e}")
        return _error_response(f"Failed to fetch joke: {str(e)}")


@router.get("/trivia/questions")
def trivia_questions(
    amount: int = Query(1, description="Number of questions"),
    category: Optional[int] = Query(None, description="Category ID"),
    difficulty: Optional[str] = Query(None, description="Difficulty: easy, medium, hard")
) -> Dict[str, Any]:
    """
    Open Trivia Database questions.

    Args:
        amount: Number of questions
        category: Optional category ID
        difficulty: Optional difficulty level

    Returns:
        Standardized response with trivia questions
    """
    try:
        url = "https://opentdb.com/api.php"
        params = {"amount": amount}
        if category:
            params["category"] = category
        if difficulty:
            params["difficulty"] = difficulty

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if data.get("response_code") == 0:
            results = data.get("results", [])
            questions = []
            for q in results:
                question = q.get("question", "")
                correct = q.get("correct_answer", "")
                questions.append(f"Q: {question} A: {correct}")

            result = _standardize_response(
                answer=f"Trivia questions: {'; '.join(questions)}",
                citations=["https://opentdb.com/"],
                metadata={"count": len(questions), "questions": results}
            )
        else:
            result = _error_response("Failed to fetch trivia questions")

        return result

    except requests.RequestException as e:
        logger.error(f"Open Trivia API error: {e}")
        return _error_response(f"Failed to fetch trivia: {str(e)}")


@router.get("/bored/activities")
def bored_activities(
    activity_type: Optional[str] = Query(None, description="Activity type"),
    participants: Optional[int] = Query(None, description="Number of participants")
) -> Dict[str, Any]:
    """
    Bored API activity suggestions.

    Args:
        activity_type: Optional activity type
        participants: Optional number of participants

    Returns:
        Standardized response with activity suggestion
    """
    try:
        url = "https://www.boredapi.com/api/activity"
        params = {}
        if activity_type:
            params["type"] = activity_type
        if participants:
            params["participants"] = participants

        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        activity = data.get("activity", "")
        activity_type_result = data.get("type", "")
        participants_result = data.get("participants", 0)

        result = _standardize_response(
            answer=f"Activity suggestion: {activity} (Type: {activity_type_result}, Participants: {participants_result})",
            citations=["https://www.boredapi.com/"],
            metadata=data
        )
        return result

    except requests.RequestException as e:
        logger.error(f"Bored API error: {e}")
        return _error_response(f"Failed to fetch activity: {str(e)}")


# ==================== HUGGING FACE MODELS ====================

@router.get("/hf/gpt2")
@router.get("/hf/sentiment")
@router.get("/hf/translate_en_es")
@router.get("/hf/translate_en_fr")
@router.get("/hf/summarization")
@router.get("/hf/question_answering")
@router.get("/hf/ner")
@router.get("/hf/image_classification")
@router.get("/ollama/llama3_8b")
def ollama_llama3_8b(
    prompt: str = Query(..., description="Prompt for Llama 3.1 8B"),
    ollama_url: str = Query("http://localhost:11434", description="Ollama server URL")
) -> Dict[str, Any]:
    """
    Ollama Llama 3.1 8B model.

    Args:
        prompt: Text prompt
        ollama_url: Ollama server URL

    Returns:
        Standardized response with model output
    """
    cache_key = _cache_key("ollama:llama3_8b", {"prompt": prompt})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = f"{ollama_url}/api/generate"
        payload = {
            "model": "llama3.1:8b",
            "prompt": prompt,
            "stream": False
        }

        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        output = data.get("response", "")

        if output:
            result = _standardize_response(
                answer=f"Llama 3.1 8B: {output}",
                citations=["https://ollama.com/library/llama3.1"],
                metadata={"prompt": prompt, "model": "llama3.1:8b"}
            )
        else:
            result = _error_response("Llama 3.1 8B generation failed")

        _cache_set(cache_key, result, CACHE_TTL_MEDIUM)
        return result

    except requests.RequestException as e:
        logger.error(f"Ollama Llama 3.1 API error: {e}")
        return _error_response(f"Failed to generate with Llama 3.1 8B: {str(e)}")


@router.get("/ollama/mistral_7b")
def ollama_mistral_7b(
    prompt: str = Query(..., description="Prompt for Mistral 7B"),
    ollama_url: str = Query("http://localhost:11434", description="Ollama server URL")
) -> Dict[str, Any]:
    """
    Ollama Mistral 7B model.

    Args:
        prompt: Text prompt
        ollama_url: Ollama server URL

    Returns:
        Standardized response with model output
    """
    cache_key = _cache_key("ollama:mistral_7b", {"prompt": prompt})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = f"{ollama_url}/api/generate"
        payload = {
            "model": "mistral:7b",
            "prompt": prompt,
            "stream": False
        }

        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        output = data.get("response", "")

        if output:
            result = _standardize_response(
                answer=f"Mistral 7B: {output}",
                citations=["https://ollama.com/library/mistral"],
                metadata={"prompt": prompt, "model": "mistral:7b"}
            )
        else:
            result = _error_response("Mistral 7B generation failed")

        _cache_set(cache_key, result, CACHE_TTL_MEDIUM)
        return result

    except requests.RequestException as e:
        logger.error(f"Ollama Mistral API error: {e}")
        return _error_response(f"Failed to generate with Mistral 7B: {str(e)}")


@router.get("/ollama/codellama_13b")
def ollama_codellama_13b(
    prompt: str = Query(..., description="Prompt for CodeLlama 13B"),
    ollama_url: str = Query("http://localhost:11434", description="Ollama server URL")
) -> Dict[str, Any]:
    """
    Ollama CodeLlama 13B model.

    Args:
        prompt: Code prompt
        ollama_url: Ollama server URL

    Returns:
        Standardized response with model output
    """
    cache_key = _cache_key("ollama:codellama_13b", {"prompt": prompt})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = f"{ollama_url}/api/generate"
        payload = {
            "model": "codellama:13b",
            "prompt": prompt,
            "stream": False
        }

        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        output = data.get("response", "")

        if output:
            result = _standardize_response(
                answer=f"CodeLlama 13B: {output}",
                citations=["https://ollama.com/library/codellama"],
                metadata={"prompt": prompt, "model": "codellama:13b"}
            )
        else:
            result = _error_response("CodeLlama 13B generation failed")

        _cache_set(cache_key, result, CACHE_TTL_MEDIUM)
        return result

    except requests.RequestException as e:
        logger.error(f"Ollama CodeLlama API error: {e}")
        return _error_response(f"Failed to generate with CodeLlama 13B: {str(e)}")


@router.get("/ollama/deepseek_coder")
def ollama_deepseek_coder(
    prompt: str = Query(..., description="Prompt for Deepseek Coder"),
    ollama_url: str = Query("http://localhost:11434", description="Ollama server URL")
) -> Dict[str, Any]:
    """
    Ollama Deepseek Coder model.

    Args:
        prompt: Code prompt
        ollama_url: Ollama server URL

    Returns:
        Standardized response with model output
    """
    cache_key = _cache_key("ollama:deepseek_coder", {"prompt": prompt})
    if cached := _cache_get(cache_key):
        return cached

    try:
        url = f"{ollama_url}/api/generate"
        payload = {
            "model": "deepseek-coder",
            "prompt": prompt,
            "stream": False
        }

        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        output = data.get("response", "")

        if output:
            result = _standardize_response(
                answer=f"Deepseek Coder: {output}",
                citations=["https://ollama.com/library/deepseek-coder"],
                metadata={"prompt": prompt, "model": "deepseek-coder"}
            )
        else:
            result = _error_response("Deepseek Coder generation failed")

        _cache_set(cache_key, result, CACHE_TTL_MEDIUM)
        return result

    except requests.RequestException as e:
        logger.error(f"Ollama Deepseek Coder API error: {e}")
        return _error_response(f"Failed to generate with Deepseek Coder: {str(e)}")


# ============================================================================
# PHASE 1: NEW ENTERTAINMENT, FOOD, KNOWLEDGE & QUOTES APIS
# ============================================================================

# ------------------------------
# Entertainment APIs (5)
# ------------------------------

@router.get("/entertainment/cat_facts")
def cat_facts() -> Dict[str, Any]:
    """
    Random cat facts from Cat Facts API.
    
    Returns:
        Standardized response with random cat fact
    """
    try:
        url = "https://catfact.ninja/fact"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        fact = data.get("fact", "")
        
        result = _standardize_response(
            answer=f"Cat Fact: {fact}",
            citations=["https://catfact.ninja"],
            metadata={"length": data.get("length", 0)}
        )
        
        _cache_set(_cache_key("cat:facts", {}), result, 3600)  # Cache for 1 hour
        return result
        
    except requests.RequestException as e:
        logger.error(f"Cat Facts API error: {e}")
        return _error_response(f"Failed to fetch cat fact: {str(e)}")


@router.get("/entertainment/dog_images")
def dog_images(
    breed: Optional[str] = Query(None, description="Specific dog breed (optional)")
) -> Dict[str, Any]:
    """
    Random dog images from Dog CEO API.
    
    Args:
        breed: Optional specific breed (e.g., 'husky', 'retriever')
    
    Returns:
        Standardized response with dog image URL
    """
    try:
        if breed:
            url = f"https://dog.ceo/api/breed/{breed.lower()}/images/random"
        else:
            url = "https://dog.ceo/api/breeds/image/random"
            
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "success":
            image_url = data.get("message", "")
            
            result = _standardize_response(
                answer=f"Random dog image: {image_url}",
                citations=["https://dog.ceo/dog-api/"],
                metadata={"breed": breed or "random", "image_url": image_url}
            )
            
            _cache_set(_cache_key("dog:images", {"breed": breed}), result, 3600)
            return result
        else:
            return _error_response("Failed to fetch dog image")
            
    except requests.RequestException as e:
        logger.error(f"Dog CEO API error: {e}")
        return _error_response(f"Failed to fetch dog image: {str(e)}")


@router.get("/entertainment/pokemon")
def pokemon_data(
    name: str = Query(..., description="Pokemon name or ID")
) -> Dict[str, Any]:
    """
    Pokemon data from PokeAPI.
    
    Args:
        name: Pokemon name (e.g., 'pikachu') or ID number
    
    Returns:
        Standardized response with Pokemon details
    """
    cache_key = _cache_key("pokemon:data", {"name": name})
    if cached := _cache_get(cache_key):
        return cached
        
    try:
        url = f"https://pokeapi.co/api/v2/pokemon/{name.lower()}"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        poke_name = data.get("name", "").capitalize()
        types = [t["type"]["name"] for t in data.get("types", [])]
        height = data.get("height", 0) / 10  # Convert to meters
        weight = data.get("weight", 0) / 10  # Convert to kg
        abilities = [a["ability"]["name"] for a in data.get("abilities", [])]
        
        answer = f"""Pokemon: {poke_name}
Type(s): {', '.join(types)}
Height: {height}m
Weight: {weight}kg
Abilities: {', '.join(abilities)}"""
        
        result = _standardize_response(
            answer=answer,
            citations=["https://pokeapi.co"],
            metadata={
                "id": data.get("id"),
                "name": poke_name,
                "types": types,
                "sprite": data.get("sprites", {}).get("front_default")
            }
        )
        
        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result
        
    except requests.RequestException as e:
        logger.error(f"PokeAPI error: {e}")
        return _error_response(f"Failed to fetch Pokemon data: {str(e)}")


@router.get("/entertainment/rick_morty")
def rick_morty_characters(
    name: Optional[str] = Query(None, description="Character name to search")
) -> Dict[str, Any]:
    """
    Rick and Morty character data.
    
    Args:
        name: Optional character name to search for
    
    Returns:
        Standardized response with character information
    """
    try:
        if name:
            url = f"https://rickandmortyapi.com/api/character/?name={name}"
        else:
            # Get a random character (ID between 1-826)
            import random
            char_id = random.randint(1, 826)
            url = f"https://rickandmortyapi.com/api/character/{char_id}"
            
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        # Handle search results vs single character
        if "results" in data:
            if data["results"]:
                char = data["results"][0]
            else:
                return _error_response(f"No character found with name: {name}")
        else:
            char = data
            
        answer = f"""Character: {char.get('name')}
Status: {char.get('status')}
Species: {char.get('species')}
Gender: {char.get('gender')}
Origin: {char.get('origin', {}).get('name')}
Location: {char.get('location', {}).get('name')}"""
        
        result = _standardize_response(
            answer=answer,
            citations=["https://rickandmortyapi.com"],
            metadata={
                "id": char.get("id"),
                "name": char.get("name"),
                "image": char.get("image")
            }
        )
        
        _cache_set(_cache_key("rick_morty:char", {"name": name}), result, CACHE_TTL_LONG)
        return result
        
    except requests.RequestException as e:
        logger.error(f"Rick and Morty API error: {e}")
        return _error_response(f"Failed to fetch character data: {str(e)}")


@router.get("/entertainment/breaking_bad")
def breaking_bad_quotes() -> Dict[str, Any]:
    """
    Random Breaking Bad quote.
    
    Returns:
        Standardized response with quote and author
    """
    try:
        url = "https://api.breakingbadquotes.xyz/v1/quotes"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if data and len(data) > 0:
            quote_data = data[0]
            quote = quote_data.get("quote", "")
            author = quote_data.get("author", "")
            
            result = _standardize_response(
                answer=f'"{quote}" - {author}',
                citations=["https://breakingbadapi.com"],
                metadata={"author": author}
            )
            
            return result
        else:
            return _error_response("No quote returned")
            
    except requests.RequestException as e:
        logger.error(f"Breaking Bad API error: {e}")
        return _error_response(f"Failed to fetch quote: {str(e)}")


# ------------------------------
# Food & Drink APIs (3)
# ------------------------------

@router.get("/food/meals")
def themealdb_recipes(
    query: Optional[str] = Query(None, description="Meal name to search"),
    category: Optional[str] = Query(None, description="Meal category (e.g., 'Seafood', 'Vegetarian')")
) -> Dict[str, Any]:
    """
    Recipe database from TheMealDB.
    
    Args:
        query: Meal name to search for
        category: Optional category filter
    
    Returns:
        Standardized response with recipe details
    """
    try:
        if query:
            url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={query}"
        elif category:
            url = f"https://www.themealdb.com/api/json/v1/1/filter.php?c={category}"
        else:
            # Random meal
            url = "https://www.themealdb.com/api/json/v1/1/random.php"
            
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        meals = data.get("meals")
        if not meals:
            return _error_response("No meals found")
            
        meal = meals[0]
        
        # Build ingredients list
        ingredients = []
        for i in range(1, 21):
            ingredient = meal.get(f"strIngredient{i}")
            measure = meal.get(f"strMeasure{i}")
            if ingredient and ingredient.strip():
                ingredients.append(f"{measure} {ingredient}".strip())
        
        answer = f"""Meal: {meal.get('strMeal')}
Category: {meal.get('strCategory')}
Area: {meal.get('strArea')}

Ingredients:
{chr(10).join('- ' + ing for ing in ingredients[:10])}

Instructions: {meal.get('strInstructions', '')[:200]}..."""
        
        result = _standardize_response(
            answer=answer,
            citations=[meal.get('strSource') or "https://www.themealdb.com"],
            metadata={
                "meal_id": meal.get("idMeal"),
                "image": meal.get("strMealThumb"),
                "youtube": meal.get("strYoutube")
            }
        )
        
        _cache_set(_cache_key("meals:recipe", {"q": query, "cat": category}), result, CACHE_TTL_LONG)
        return result
        
    except requests.RequestException as e:
        logger.error(f"TheMealDB API error: {e}")
        return _error_response(f"Failed to fetch recipe: {str(e)}")


@router.get("/food/cocktails")
def cocktaildb_recipes(
    query: Optional[str] = Query(None, description="Cocktail name to search")
) -> Dict[str, Any]:
    """
    Cocktail recipes from TheCocktailDB.
    
    Args:
        query: Cocktail name to search for
    
    Returns:
        Standardized response with cocktail recipe
    """
    try:
        if query:
            url = f"https://www.thecocktaildb.com/api/json/v1/1/search.php?s={query}"
        else:
            # Random cocktail
            url = "https://www.thecocktaildb.com/api/json/v1/1/random.php"
            
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        drinks = data.get("drinks")
        if not drinks:
            return _error_response("No cocktails found")
            
        drink = drinks[0]
        
        # Build ingredients list
        ingredients = []
        for i in range(1, 16):
            ingredient = drink.get(f"strIngredient{i}")
            measure = drink.get(f"strMeasure{i}")
            if ingredient and ingredient.strip():
                ingredients.append(f"{measure or ''} {ingredient}".strip())
        
        answer = f"""Cocktail: {drink.get('strDrink')}
Category: {drink.get('strCategory')}
Glass: {drink.get('strGlass')}
Alcoholic: {drink.get('strAlcoholic')}

Ingredients:
{chr(10).join('- ' + ing for ing in ingredients)}

Instructions: {drink.get('strInstructions')}"""
        
        result = _standardize_response(
            answer=answer,
            citations=["https://www.thecocktaildb.com"],
            metadata={
                "drink_id": drink.get("idDrink"),
                "image": drink.get("strDrinkThumb")
            }
        )
        
        _cache_set(_cache_key("cocktails:recipe", {"q": query}), result, CACHE_TTL_LONG)
        return result
        
    except requests.RequestException as e:
        logger.error(f"CocktailDB API error: {e}")
        return _error_response(f"Failed to fetch cocktail recipe: {str(e)}")


@router.get("/food/fruits")
def fruityvice_nutrition(
    fruit: str = Query(..., description="Fruit name (e.g., 'banana', 'apple')")
) -> Dict[str, Any]:
    """
    Fruit nutrition data from Fruityvice.
    
    Args:
        fruit: Fruit name to get nutrition info for
    
    Returns:
        Standardized response with nutrition facts
    """
    cache_key = _cache_key("fruit:nutrition", {"fruit": fruit})
    if cached := _cache_get(cache_key):
        return cached
        
    try:
        url = f"https://fruityvice.com/api/fruit/{fruit.lower()}"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        nutritions = data.get("nutritions", {})
        
        answer = f"""Fruit: {data.get('name')}
Family: {data.get('family')}
Order: {data.get('order')}
Genus: {data.get('genus')}

Nutritional Information (per 100g):
- Calories: {nutritions.get('calories')} kcal
- Fat: {nutritions.get('fat')}g
- Sugar: {nutritions.get('sugar')}g
- Carbohydrates: {nutritions.get('carbohydrates')}g
- Protein: {nutritions.get('protein')}g"""
        
        result = _standardize_response(
            answer=answer,
            citations=["https://fruityvice.com"],
            metadata={"fruit": data.get("name"), "nutritions": nutritions}
        )
        
        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result
        
    except requests.RequestException as e:
        logger.error(f"Fruityvice API error: {e}")
        return _error_response(f"Failed to fetch fruit data: {str(e)}")


# ------------------------------
# Knowledge & Education APIs (4)
# ------------------------------

@router.get("/knowledge/universities")
def universities_search(
    country: Optional[str] = Query(None, description="Country name or code"),
    name: Optional[str] = Query(None, description="University name to search")
) -> Dict[str, Any]:
    """
    World universities database.
    
    Args:
        country: Country name (e.g., 'United States') or code (e.g., 'US')
        name: University name to search
    
    Returns:
        Standardized response with university information
    """
    try:
        params = {}
        if country:
            params["country"] = country
        if name:
            params["name"] = name
            
        if not params:
            return _error_response("Please provide either country or name parameter")
            
        url = "http://universities.hipolabs.com/search"
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return _error_response("No universities found")
            
        # Return top 5 results
        universities = data[:5]
        
        results = []
        for uni in universities:
            results.append(f"""
{uni.get('name')}
- Country: {uni.get('country')}
- Website: {', '.join(uni.get('web_pages', []))}
- Domains: {', '.join(uni.get('domains', []))}""")
        
        answer = f"Found {len(data)} universities. Showing top {len(universities)}:" + "\n".join(results)
        
        result = _standardize_response(
            answer=answer,
            citations=[universities[0].get('web_pages', [''])[0] if universities[0].get('web_pages') else "http://universities.hipolabs.com"],
            metadata={"total_results": len(data), "displayed": len(universities)}
        )
        
        _cache_set(_cache_key("universities:search", params), result, CACHE_TTL_LONG)
        return result
        
    except requests.RequestException as e:
        logger.error(f"Universities API error: {e}")
        return _error_response(f"Failed to fetch universities: {str(e)}")


@router.get("/knowledge/zipcode")
def zippopotam_lookup(
    country: str = Query(..., description="Country code (e.g., 'US', 'GB')"),
    zipcode: str = Query(..., description="Postal/ZIP code")
) -> Dict[str, Any]:
    """
    Zip code / postal code lookup via Zippopotam.
    
    Args:
        country: Country code (ISO 3166-1 alpha-2)
        zipcode: Postal or ZIP code
    
    Returns:
        Standardized response with location details
    """
    cache_key = _cache_key("zipcode:lookup", {"country": country, "zip": zipcode})
    if cached := _cache_get(cache_key):
        return cached
        
    try:
        url = f"http://api.zippopotam.us/{country.upper()}/{zipcode}"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        places = data.get("places", [])
        
        if places:
            place = places[0]
            answer = f"""ZIP/Postal Code: {data.get('post code')}
Country: {data.get('country')} ({data.get('country abbreviation')})
Place: {place.get('place name')}
State: {place.get('state')} ({place.get('state abbreviation')})
Latitude: {place.get('latitude')}
Longitude: {place.get('longitude')}"""
        else:
            answer = f"ZIP code {zipcode} found in {data.get('country')}, but no place details available"
        
        result = _standardize_response(
            answer=answer,
            citations=["http://www.zippopotam.us"],
            metadata={
                "post_code": data.get("post code"),
                "country": data.get("country"),
                "places": places
            }
        )
        
        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result
        
    except requests.RequestException as e:
        logger.error(f"Zippopotam API error: {e}")
        return _error_response(f"Failed to lookup ZIP code: {str(e)}")


@router.get("/knowledge/agify")
def agify_predict_age(
    name: str = Query(..., description="First name to predict age from")
) -> Dict[str, Any]:
    """
    Predict age based on first name using Agify.io.
    
    Args:
        name: First name to analyze
    
    Returns:
        Standardized response with age prediction
    """
    cache_key = _cache_key("agify:age", {"name": name})
    if cached := _cache_get(cache_key):
        return cached
        
    try:
        url = f"https://api.agify.io/?name={name}"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        age = data.get("age")
        count = data.get("count", 0)
        
        if age:
            answer = f"""Name: {data.get('name')}
Predicted Age: {age} years old
Confidence: Based on {count:,} data points"""
        else:
            answer = f"Unable to predict age for name: {name}"
        
        result = _standardize_response(
            answer=answer,
            citations=["https://agify.io"],
            metadata={"name": name, "age": age, "count": count}
        )
        
        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result
        
    except requests.RequestException as e:
        logger.error(f"Agify API error: {e}")
        return _error_response(f"Failed to predict age: {str(e)}")


@router.get("/knowledge/nationalize")
def nationalize_predict_nationality(
    name: str = Query(..., description="First name to predict nationality from")
) -> Dict[str, Any]:
    """
    Predict nationality based on first name using Nationalize.io.
    
    Args:
        name: First name to analyze
    
    Returns:
        Standardized response with nationality predictions
    """
    cache_key = _cache_key("nationalize:country", {"name": name})
    if cached := _cache_get(cache_key):
        return cached
        
    try:
        url = f"https://api.nationalize.io/?name={name}"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        countries = data.get("country", [])
        
        if countries:
            # Sort by probability
            countries_sorted = sorted(countries, key=lambda x: x.get("probability", 0), reverse=True)
            
            predictions = []
            for country in countries_sorted[:5]:
                country_id = country.get("country_id")
                probability = country.get("probability", 0) * 100
                predictions.append(f"- {country_id}: {probability:.1f}% probability")
            
            answer = f"""Name: {data.get('name')}
Predicted Nationalities:
{chr(10).join(predictions)}"""
        else:
            answer = f"Unable to predict nationality for name: {name}"
        
        result = _standardize_response(
            answer=answer,
            citations=["https://nationalize.io"],
            metadata={"name": name, "countries": countries}
        )
        
        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result
        
    except requests.RequestException as e:
        logger.error(f"Nationalize API error: {e}")
        return _error_response(f"Failed to predict nationality: {str(e)}")


# ------------------------------
# Quotes & Advice APIs (3)
# ------------------------------

@router.get("/quotes/advice")
def adviceslip_random() -> Dict[str, Any]:
    """
    Random advice from Advice Slip API.
    
    Returns:
        Standardized response with random advice
    """
    try:
        url = "https://api.adviceslip.com/advice"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        slip = data.get("slip", {})
        advice = slip.get("advice", "")
        
        result = _standardize_response(
            answer=f"Advice: {advice}",
            citations=["https://adviceslip.com"],
            metadata={"advice_id": slip.get("id")}
        )
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"Advice Slip API error: {e}")
        return _error_response(f"Failed to fetch advice: {str(e)}")


@router.get("/quotes/quotable")
def quotable_random(
    tags: Optional[str] = Query(None, description="Comma-separated tags (e.g., 'wisdom,inspirational')")
) -> Dict[str, Any]:
    """
    Random quotes from Quotable API.
    
    Args:
        tags: Optional tags to filter quotes
    
    Returns:
        Standardized response with random quote
    """
    try:
        url = "https://api.quotable.io/random"
        params = {}
        if tags:
            params["tags"] = tags
            
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        content = data.get("content", "")
        author = data.get("author", "")
        quote_tags = data.get("tags", [])
        
        answer = f'"{content}" - {author}'
        if quote_tags:
            answer += f"\n\nTags: {', '.join(quote_tags)}"
        
        result = _standardize_response(
            answer=answer,
            citations=["https://quotable.io"],
            metadata={
                "author": author,
                "tags": quote_tags,
                "length": data.get("length")
            }
        )
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"Quotable API error: {e}")
        return _error_response(f"Failed to fetch quote: {str(e)}")


@router.get("/quotes/zenquotes")
def zenquotes_random() -> Dict[str, Any]:
    """
    Inspirational quotes from ZenQuotes API.
    
    Returns:
        Standardized response with inspirational quote
    """
    try:
        url = "https://zenquotes.io/api/random"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if data and len(data) > 0:
            quote_data = data[0]
            quote = quote_data.get("q", "")
            author = quote_data.get("a", "")
            
            result = _standardize_response(
                answer=f'"{quote}" - {author}',
                citations=["https://zenquotes.io"],
                metadata={"author": author}
            )
            
            return result
        else:
            return _error_response("No quote returned")
            
    except requests.RequestException as e:
        logger.error(f"ZenQuotes API error: {e}")
        return _error_response(f"Failed to fetch quote: {str(e)}")



# ============================================================================
# PHASE 2: UTILITY, SCIENCE, MATH & LANGUAGE APIS
# ============================================================================

# ------------------------------
# Fun & Games APIs (8)
# ------------------------------

@router.get("/fun/numbers")
def numbers_trivia(
    number: str = Query(..., description="Number to get trivia about (or 'random')")
) -> Dict[str, Any]:
    """
    Number trivia from Numbers API.
    
    Args:
        number: Number to get trivia about, or 'random' for random number
    
    Returns:
        Standardized response with number trivia
    """
    cache_key = _cache_key("numbers:trivia", {"number": number})
    if cached := _cache_get(cache_key):
        return cached
        
    try:
        url = f"http://numbersapi.com/{number}"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        trivia = response.text
        
        result = _standardize_response(
            answer=f"Number Trivia: {trivia}",
            citations=["http://numbersapi.com"],
            metadata={"number": number}
        )
        
        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result
        
    except requests.RequestException as e:
        logger.error(f"Numbers API error: {e}")
        return _error_response(f"Failed to fetch number trivia: {str(e)}")


@router.get("/fun/useless_facts")
def useless_facts() -> Dict[str, Any]:
    """
    Random useless facts.
    
    Returns:
        Standardized response with random useless fact
    """
    try:
        url = "https://uselessfacts.jsph.pl/random.json?language=en"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        fact = data.get("text", "")
        
        result = _standardize_response(
            answer=f"Useless Fact: {fact}",
            citations=["https://uselessfacts.jsph.pl"],
            metadata={"id": data.get("id")}
        )
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"Useless Facts API error: {e}")
        return _error_response(f"Failed to fetch useless fact: {str(e)}")


@router.get("/fun/chuck_norris")
def chuck_norris_jokes(
    category: Optional[str] = Query(None, description="Joke category (optional)")
) -> Dict[str, Any]:
    """
    Chuck Norris jokes from official API.
    
    Args:
        category: Optional category filter
    
    Returns:
        Standardized response with Chuck Norris joke
    """
    try:
        if category:
            url = f"https://api.chucknorris.io/jokes/random?category={category}"
        else:
            url = "https://api.chucknorris.io/jokes/random"
            
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        joke = data.get("value", "")
        
        result = _standardize_response(
            answer=f"Chuck Norris Joke: {joke}",
            citations=["https://api.chucknorris.io"],
            metadata={"category": data.get("categories", [])}
        )
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"Chuck Norris API error: {e}")
        return _error_response(f"Failed to fetch Chuck Norris joke: {str(e)}")


@router.get("/fun/kanye_quotes")
def kanye_quotes() -> Dict[str, Any]:
    """
    Random Kanye West quotes.
    
    Returns:
        Standardized response with Kanye quote
    """
    try:
        url = "https://api.kanye.rest/"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        quote = data.get("quote", "")
        
        result = _standardize_response(
            answer=f'Kanye West: "{quote}"',
            citations=["https://kanye.rest"],
            metadata={}
        )
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"Kanye REST API error: {e}")
        return _error_response(f"Failed to fetch Kanye quote: {str(e)}")


@router.get("/fun/corporate_bs")
def corporate_bs() -> Dict[str, Any]:
    """
    Corporate buzzword generator.
    
    Returns:
        Standardized response with corporate buzzword phrase
    """
    try:
        url = "https://corporatebs-generator.sameerkumar.website/"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        phrase = data.get("phrase", "")
        
        result = _standardize_response(
            answer=f"Corporate BS: {phrase}",
            citations=["https://corporatebs-generator.sameerkumar.website"],
            metadata={}
        )
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"Corporate BS API error: {e}")
        return _error_response(f"Failed to fetch corporate BS: {str(e)}")


@router.get("/fun/yesno")
def yesno_answer() -> Dict[str, Any]:
    """
    Random yes/no answer with GIF.
    
    Returns:
        Standardized response with yes/no answer
    """
    try:
        url = "https://yesno.wtf/api"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        answer = data.get("answer", "").upper()
        image = data.get("image", "")
        
        result = _standardize_response(
            answer=f"Answer: {answer}",
            citations=["https://yesno.wtf"],
            metadata={"answer": answer, "image": image}
        )
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"YesNo API error: {e}")
        return _error_response(f"Failed to get yes/no answer: {str(e)}")


@router.get("/fun/coinflip")
def coinflip() -> Dict[str, Any]:
    """
    Coin flip simulation.
    
    Returns:
        Standardized response with heads or tails
    """
    import random
    
    result_value = random.choice(["Heads", "Tails"])
    
    result = _standardize_response(
        answer=f"Coin Flip Result: {result_value}",
        citations=["internal"],
        metadata={"result": result_value}
    )
    
    return result


@router.get("/fun/dice_roll")
def dice_roll(
    sides: int = Query(6, description="Number of sides on the die"),
    count: int = Query(1, description="Number of dice to roll")
) -> Dict[str, Any]:
    """
    Dice roll simulation.
    
    Args:
        sides: Number of sides on each die (default: 6)
        count: Number of dice to roll (default: 1)
    
    Returns:
        Standardized response with dice roll results
    """
    import random
    
    if count > 20:
        return _error_response("Maximum 20 dice allowed")
    if sides < 2 or sides > 100:
        return _error_response("Sides must be between 2 and 100")
    
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls)
    
    answer = f"Rolled {count}d{sides}: {rolls}\nTotal: {total}"
    
    result = _standardize_response(
        answer=answer,
        citations=["internal"],
        metadata={"rolls": rolls, "total": total, "sides": sides, "count": count}
    )
    
    return result


# ------------------------------
# Utility APIs (7)
# ------------------------------

@router.get("/utilities/ipify")
def ipify_public_ip() -> Dict[str, Any]:
    """
    Get public IP address using ipify.
    
    Returns:
        Standardized response with public IP
    """
    try:
        url = "https://api.ipify.org?format=json"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        ip = data.get("ip", "")
        
        result = _standardize_response(
            answer=f"Your Public IP: {ip}",
            citations=["https://www.ipify.org"],
            metadata={"ip": ip}
        )
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"Ipify API error: {e}")
        return _error_response(f"Failed to get public IP: {str(e)}")


@router.get("/utilities/uuid")
def uuid_generator(
    count: int = Query(1, description="Number of UUIDs to generate (max 10)")
) -> Dict[str, Any]:
    """
    Generate UUID(s).
    
    Args:
        count: Number of UUIDs to generate
    
    Returns:
        Standardized response with UUID(s)
    """
    import uuid
    
    if count > 10:
        return _error_response("Maximum 10 UUIDs allowed")
    
    uuids = [str(uuid.uuid4()) for _ in range(count)]
    
    if count == 1:
        answer = f"UUID: {uuids[0]}"
    else:
        answer = f"Generated {count} UUIDs:\n" + "\n".join(f"{i+1}. {u}" for i, u in enumerate(uuids))
    
    result = _standardize_response(
        answer=answer,
        citations=["internal"],
        metadata={"uuids": uuids, "count": count}
    )
    
    return result


@router.get("/utilities/color_info")
def color_info(
    color: str = Query(..., description="Color hex code (without #) or name")
) -> Dict[str, Any]:
    """
    Get color information from The Color API.
    
    Args:
        color: Color hex code (e.g., 'FF5733') or name (e.g., 'red')
    
    Returns:
        Standardized response with color details
    """
    cache_key = _cache_key("color:info", {"color": color})
    if cached := _cache_get(cache_key):
        return cached
        
    try:
        # Remove # if present
        color = color.replace("#", "")
        
        url = f"https://www.thecolorapi.com/id?hex={color}"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        hex_value = data.get("hex", {}).get("value", "")
        rgb = data.get("rgb", {}).get("value", "")
        name = data.get("name", {}).get("value", "")
        
        answer = f"""Color: {name}
HEX: {hex_value}
RGB: {rgb}
HSL: {data.get("hsl", {}).get("value", "")}"""
        
        result = _standardize_response(
            answer=answer,
            citations=["https://www.thecolorapi.com"],
            metadata={"hex": hex_value, "name": name}
        )
        
        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result
        
    except requests.RequestException as e:
        logger.error(f"Color API error: {e}")
        return _error_response(f"Failed to get color info: {str(e)}")


@router.get("/utilities/base64_encode")
def base64_encode(
    text: str = Query(..., description="Text to encode")
) -> Dict[str, Any]:
    """
    Encode text to Base64.
    
    Args:
        text: Text to encode
    
    Returns:
        Standardized response with Base64 encoded text
    """
    import base64
    
    try:
        encoded = base64.b64encode(text.encode('utf-8')).decode('utf-8')
        
        result = _standardize_response(
            answer=f"Base64 Encoded: {encoded}",
            citations=["internal"],
            metadata={"original": text, "encoded": encoded}
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Base64 encoding error: {e}")
        return _error_response(f"Failed to encode: {str(e)}")


@router.get("/utilities/base64_decode")
def base64_decode(
    encoded: str = Query(..., description="Base64 text to decode")
) -> Dict[str, Any]:
    """
    Decode Base64 to text.
    
    Args:
        encoded: Base64 encoded text to decode
    
    Returns:
        Standardized response with decoded text
    """
    import base64
    
    try:
        decoded = base64.b64decode(encoded.encode('utf-8')).decode('utf-8')
        
        result = _standardize_response(
            answer=f"Decoded: {decoded}",
            citations=["internal"],
            metadata={"encoded": encoded, "decoded": decoded}
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Base64 decoding error: {e}")
        return _error_response(f"Failed to decode: {str(e)}")


@router.get("/utilities/httpbin_test")
def httpbin_test(
    endpoint: str = Query("get", description="Endpoint to test (get, post, headers, ip, user-agent)")
) -> Dict[str, Any]:
    """
    HTTP request/response testing via httpbin.
    
    Args:
        endpoint: Which httpbin endpoint to test
    
    Returns:
        Standardized response with httpbin test results
    """
    try:
        url = f"https://httpbin.org/{endpoint}"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        result = _standardize_response(
            answer=f"HTTPBin Test ({endpoint}): {str(data)[:200]}...",
            citations=["https://httpbin.org"],
            metadata={"endpoint": endpoint, "data": data}
        )
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"HTTPBin API error: {e}")
        return _error_response(f"Failed to test with HTTPBin: {str(e)}")


@router.get("/utilities/postman_echo")
def postman_echo(
    message: str = Query(..., description="Message to echo back")
) -> Dict[str, Any]:
    """
    Echo service from Postman Echo API.
    
    Args:
        message: Message to echo
    
    Returns:
        Standardized response with echoed message
    """
    try:
        url = "https://postman-echo.com/get"
        params = {"message": message}
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        echoed = data.get("args", {}).get("message", "")
        
        result = _standardize_response(
            answer=f"Echo: {echoed}",
            citations=["https://postman-echo.com"],
            metadata={"original": message, "echoed": echoed}
        )
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"Postman Echo API error: {e}")
        return _error_response(f"Failed to echo message: {str(e)}")


# ------------------------------
# Science & Math APIs (5)
# ------------------------------

@router.get("/science/newton_math")
def newton_math(
    operation: str = Query(..., description="Math operation (simplify, factor, derive, integrate, zeroes, area, cos, sin, tan, log, abs)"),
    expression: str = Query(..., description="Math expression to compute")
) -> Dict[str, Any]:
    """
    Symbolic math operations via Newton API.
    
    Args:
        operation: Type of operation
        expression: Math expression
    
    Returns:
        Standardized response with math result
    """
    cache_key = _cache_key("newton:math", {"op": operation, "expr": expression})
    if cached := _cache_get(cache_key):
        return cached
        
    try:
        url = f"https://newton.now.sh/api/v2/{operation}/{expression}"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        operation_name = data.get("operation", "")
        expr = data.get("expression", "")
        answer_value = data.get("result", "")
        
        answer = f"""Operation: {operation_name}
Expression: {expr}
Result: {answer_value}"""
        
        result = _standardize_response(
            answer=answer,
            citations=["https://newton.now.sh"],
            metadata={"operation": operation_name, "result": answer_value}
        )
        
        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result
        
    except requests.RequestException as e:
        logger.error(f"Newton Math API error: {e}")
        return _error_response(f"Failed to compute math: {str(e)}")


@router.get("/science/periodic_table")
def periodic_table(
    element: str = Query(..., description="Element symbol or name (e.g., 'H', 'Hydrogen')")
) -> Dict[str, Any]:
    """
    Periodic table element data.
    
    Args:
        element: Element symbol or name
    
    Returns:
        Standardized response with element details
    """
    cache_key = _cache_key("periodic:element", {"element": element})
    if cached := _cache_get(cache_key):
        return cached
        
    try:
        # Try by symbol first, then by name
        url = f"https://neelpatel05.pythonanywhere.com/element/symbol/{element.upper()}"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        
        if response.status_code == 404:
            # Try by name
            url = f"https://neelpatel05.pythonanywhere.com/element/name/{element.capitalize()}"
            response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        
        response.raise_for_status()
        data = response.json()
        
        answer = f"""Element: {data.get('name')} ({data.get('symbol')})
Atomic Number: {data.get('atomicNumber')}
Atomic Mass: {data.get('atomicMass')}
Category: {data.get('groupBlock')}
Electron Configuration: {data.get('electronicConfiguration')}
Discovered By: {data.get('discoveredBy', 'Unknown')}"""
        
        result = _standardize_response(
            answer=answer,
            citations=["https://neelpatel05.pythonanywhere.com"],
            metadata={
                "name": data.get("name"),
                "symbol": data.get("symbol"),
                "atomicNumber": data.get("atomicNumber")
            }
        )
        
        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result
        
    except requests.RequestException as e:
        logger.error(f"Periodic Table API error: {e}")
        return _error_response(f"Failed to get element data: {str(e)}")


@router.get("/science/sunrise_sunset")
def sunrise_sunset(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    date: Optional[str] = Query(None, description="Date (YYYY-MM-DD), defaults to today")
) -> Dict[str, Any]:
    """
    Sunrise and sunset times for a location.
    
    Args:
        lat: Latitude
        lng: Longitude
        date: Optional date (defaults to today)
    
    Returns:
        Standardized response with sunrise/sunset times
    """
    cache_key = _cache_key("sun:times", {"lat": lat, "lng": lng, "date": date})
    if cached := _cache_get(cache_key):
        return cached
        
    try:
        params = {"lat": lat, "lng": lng, "formatted": 0}
        if date:
            params["date"] = date
            
        url = "https://api.sunrise-sunset.org/json"
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "OK":
            results = data.get("results", {})
            
            answer = f"""Sunrise: {results.get('sunrise')}
Sunset: {results.get('sunset')}
Solar Noon: {results.get('solar_noon')}
Day Length: {results.get('day_length')} seconds
Civil Twilight Begin: {results.get('civil_twilight_begin')}
Civil Twilight End: {results.get('civil_twilight_end')}"""
            
            result = _standardize_response(
                answer=answer,
                citations=["https://sunrise-sunset.org"],
                metadata={"lat": lat, "lng": lng, "results": results}
            )
            
            _cache_set(cache_key, result, CACHE_TTL_MEDIUM)
            return result
        else:
            return _error_response("Invalid location or date")
            
    except requests.RequestException as e:
        logger.error(f"Sunrise-Sunset API error: {e}")
        return _error_response(f"Failed to get sunrise/sunset times: {str(e)}")


@router.get("/science/random_user_data")
def random_user_data(
    gender: Optional[str] = Query(None, description="Gender filter (male/female)"),
    nat: Optional[str] = Query(None, description="Nationality code (e.g., US, GB, FR)")
) -> Dict[str, Any]:
    """
    Generate random user data from RandomUser API.
    
    Args:
        gender: Optional gender filter
        nat: Optional nationality code
    
    Returns:
        Standardized response with random user data
    """
    try:
        params = {}
        if gender:
            params["gender"] = gender
        if nat:
            params["nat"] = nat
            
        url = "https://randomuser.me/api/"
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if data.get("results"):
            user = data["results"][0]
            name = user.get("name", {})
            location = user.get("location", {})
            
            answer = f"""Random User:
Name: {name.get('title')} {name.get('first')} {name.get('last')}
Gender: {user.get('gender')}
Email: {user.get('email')}
Phone: {user.get('phone')}
Location: {location.get('city')}, {location.get('state')}, {location.get('country')}
Age: {user.get('dob', {}).get('age')}"""
            
            result = _standardize_response(
                answer=answer,
                citations=["https://randomuser.me"],
                metadata={"user": user}
            )
            
            return result
        else:
            return _error_response("No user data returned")
            
    except requests.RequestException as e:
        logger.error(f"RandomUser API error: {e}")
        return _error_response(f"Failed to generate random user: {str(e)}")


@router.get("/science/space_people")
def space_people() -> Dict[str, Any]:
    """
    Get list of people currently in space.
    
    Returns:
        Standardized response with astronauts in space
    """
    cache_key = _cache_key("space:people", {})
    if cached := _cache_get(cache_key):
        return cached
        
    try:
        url = "http://api.open-notify.org/astros.json"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        number = data.get("number", 0)
        people = data.get("people", [])
        
        people_list = []
        for person in people:
            people_list.append(f"- {person.get('name')} ({person.get('craft')})")
        
        answer = f"""People in Space: {number}

{chr(10).join(people_list)}"""
        
        result = _standardize_response(
            answer=answer,
            citations=["http://open-notify.org"],
            metadata={"number": number, "people": people}
        )
        
        _cache_set(cache_key, result, 3600)  # Cache for 1 hour
        return result
        
    except requests.RequestException as e:
        logger.error(f"Space People API error: {e}")
        return _error_response(f"Failed to get astronauts in space: {str(e)}")


# ------------------------------
# Language & Text APIs (5)
# ------------------------------

@router.get("/language/lorem_ipsum")
def lorem_ipsum(
    paragraphs: int = Query(1, description="Number of paragraphs (1-10)"),
    length: str = Query("medium", description="Length: short, medium, long")
) -> Dict[str, Any]:
    """
    Generate Lorem Ipsum placeholder text.
    
    Args:
        paragraphs: Number of paragraphs
        length: Length per paragraph
    
    Returns:
        Standardized response with Lorem Ipsum text
    """
    if paragraphs > 10:
        return _error_response("Maximum 10 paragraphs allowed")
        
    try:
        url = f"https://loripsum.net/api/{paragraphs}/{length}/plaintext"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        text = response.text
        
        result = _standardize_response(
            answer=f"Lorem Ipsum ({paragraphs} paragraphs):\n\n{text}",
            citations=["https://loripsum.net"],
            metadata={"paragraphs": paragraphs, "length": length}
        )
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"Lorem Ipsum API error: {e}")
        return _error_response(f"Failed to generate Lorem Ipsum: {str(e)}")


@router.get("/language/language_detect")
def language_detect(
    text: str = Query(..., description="Text to detect language")
) -> Dict[str, Any]:
    """
    Detect language of text using LibreTranslate.
    
    Args:
        text: Text to analyze
    
    Returns:
        Standardized response with detected language
    """
    cache_key = _cache_key("lang:detect", {"text": text[:100]})
    if cached := _cache_get(cache_key):
        return cached
        
    try:
        url = "https://libretranslate.de/detect"
        payload = {"q": text}
        response = requests.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if data and len(data) > 0:
            detected = data[0]
            language = detected.get("language", "")
            confidence = detected.get("confidence", 0) * 100
            
            answer = f"""Detected Language: {language}
Confidence: {confidence:.1f}%"""
            
            result = _standardize_response(
                answer=answer,
                citations=["https://libretranslate.com"],
                metadata={"language": language, "confidence": confidence}
            )
            
            _cache_set(cache_key, result, CACHE_TTL_LONG)
            return result
        else:
            return _error_response("Could not detect language")
            
    except requests.RequestException as e:
        logger.error(f"Language Detection API error: {e}")
        return _error_response(f"Failed to detect language: {str(e)}")


@router.get("/language/word_definition")
def word_definition(
    word: str = Query(..., description="Word to define")
) -> Dict[str, Any]:
    """
    Get word definition from Free Dictionary API.
    
    Args:
        word: Word to look up
    
    Returns:
        Standardized response with definition
    """
    cache_key = _cache_key("dict:define", {"word": word})
    if cached := _cache_get(cache_key):
        return cached
        
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word.lower()}"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if data and len(data) > 0:
            entry = data[0]
            meanings = entry.get("meanings", [])
            
            definitions = []
            for meaning in meanings[:3]:  # First 3 meanings
                part_of_speech = meaning.get("partOfSpeech", "")
                defs = meaning.get("definitions", [])
                if defs:
                    definition = defs[0].get("definition", "")
                    definitions.append(f"({part_of_speech}) {definition}")
            
            phonetic = entry.get("phonetic", "")
            
            answer = f"""Word: {word}
Phonetic: {phonetic}

Definitions:
{chr(10).join(f"{i+1}. {d}" for i, d in enumerate(definitions))}"""
            
            result = _standardize_response(
                answer=answer,
                citations=["https://dictionaryapi.dev"],
                metadata={"word": word, "phonetic": phonetic}
            )
            
            _cache_set(cache_key, result, CACHE_TTL_LONG)
            return result
        else:
            return _error_response(f"No definition found for: {word}")
            
    except requests.RequestException as e:
        logger.error(f"Dictionary API error: {e}")
        return _error_response(f"Failed to get definition: {str(e)}")


@router.get("/language/word_synonyms")
def word_synonyms(
    word: str = Query(..., description="Word to find synonyms for")
) -> Dict[str, Any]:
    """
    Find synonyms using Datamuse API.
    
    Args:
        word: Word to find synonyms for
    
    Returns:
        Standardized response with synonyms
    """
    cache_key = _cache_key("synonyms:word", {"word": word})
    if cached := _cache_get(cache_key):
        return cached
        
    try:
        url = "https://api.datamuse.com/words"
        params = {"rel_syn": word, "max": 20}
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if data:
            synonyms = [item.get("word", "") for item in data[:15]]
            
            answer = f"""Synonyms for "{word}":

{', '.join(synonyms)}"""
            
            result = _standardize_response(
                answer=answer,
                citations=["https://www.datamuse.com"],
                metadata={"word": word, "synonyms": synonyms}
            )
            
            _cache_set(cache_key, result, CACHE_TTL_LONG)
            return result
        else:
            return _error_response(f"No synonyms found for: {word}")
            
    except requests.RequestException as e:
        logger.error(f"Datamuse API error: {e}")
        return _error_response(f"Failed to get synonyms: {str(e)}")


@router.get("/language/gender_from_name")
def gender_from_name(
    name: str = Query(..., description="First name to predict gender from")
) -> Dict[str, Any]:
    """
    Predict gender based on first name using Genderize.io.
    
    Args:
        name: First name to analyze
    
    Returns:
        Standardized response with gender prediction
    """
    cache_key = _cache_key("gender:name", {"name": name})
    if cached := _cache_get(cache_key):
        return cached
        
    try:
        url = f"https://api.genderize.io/?name={name}"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        gender = data.get("gender", "unknown")
        probability = data.get("probability", 0) * 100
        count = data.get("count", 0)
        
        if gender != "unknown":
            answer = f"""Name: {data.get('name')}
Predicted Gender: {gender.capitalize()}
Probability: {probability:.1f}%
Based on: {count:,} data points"""
        else:
            answer = f"Unable to predict gender for name: {name}"
        
        result = _standardize_response(
            answer=answer,
            citations=["https://genderize.io"],
            metadata={"name": name, "gender": gender, "probability": probability}
        )
        
        _cache_set(cache_key, result, CACHE_TTL_LONG)
        return result
        
    except requests.RequestException as e:
        logger.error(f"Genderize API error: {e}")
        return _error_response(f"Failed to predict gender: {str(e)}")



