"""
Inline first-party provider endpoints. These are the public-data fallback
providers Axiomeer hosts itself (Open-Meteo, Wikipedia, REST Countries, etc.)
so manifests can point at /providers/* on the same host.
"""
from __future__ import annotations

from datetime import datetime, timezone

import requests
from fastapi import APIRouter

from apps.api.dependencies import cache_get, cache_key, cache_set
from marketplace.settings import (
    PROVIDER_CACHE_TTL_DICTIONARY,
    PROVIDER_CACHE_TTL_FX,
    PROVIDER_CACHE_TTL_OPENLIB,
    PROVIDER_CACHE_TTL_RESTCOUNTRIES,
    PROVIDER_CACHE_TTL_WEATHER,
    PROVIDER_CACHE_TTL_WIKI,
    PROVIDER_CACHE_TTL_WIKIDATA,
    PROVIDER_CACHE_TTL_WIKIDUMPS,
)

router = APIRouter(tags=["providers-inline"])


@router.get("/providers/openmeteo_weather")
def provider_openmeteo_weather(
    lat: float | None = None,
    lon: float | None = None,
    timezone_name: str | None = None,
):
    now = datetime.now(timezone.utc).isoformat()
    if lat is None or lon is None:
        return {
            "answer": "Missing required parameters: lat and lon.",
            "citations": [],
            "retrieved_at": now,
            "quality": "verified",
        }
    timezone_name = timezone_name or "UTC"

    key = cache_key("provider:openmeteo", {"lat": lat, "lon": lon, "timezone_name": timezone_name})
    cached = cache_get(key)
    if cached:
        return cached

    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,weather_code,wind_speed_10m",
            "timezone": timezone_name,
        },
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    current = data.get("current", {})
    res = {
        "answer": (
            f"At {current.get('time','')}, temperature is {current.get('temperature_2m')} C, "
            f"weather_code={current.get('weather_code')}, wind_speed={current.get('wind_speed_10m')} km/h (Open-Meteo)."
        ),
        "citations": ["https://open-meteo.com/"],
        "retrieved_at": now,
        "quality": "verified",
    }
    cache_set(key, res, PROVIDER_CACHE_TTL_WEATHER)
    return res


@router.get("/providers/wikipedia")
def provider_wikipedia(q: str | None = None):
    now = datetime.now(timezone.utc).isoformat()
    if not q or not q.strip():
        return {"answer": "No query provided. Please specify a topic to search.",
                "citations": [], "retrieved_at": now, "quality": "verified"}

    key = cache_key("provider:wikipedia", {"q": q.strip()})
    cached = cache_get(key)
    if cached:
        return cached

    r = requests.get(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{q}",
        timeout=10,
        headers={"User-Agent": "Axiomeer/0.1"},
    )
    if r.status_code == 404:
        res = {"answer": f"No Wikipedia article found for '{q}'.",
               "citations": [], "retrieved_at": now, "quality": "verified"}
        cache_set(key, res, PROVIDER_CACHE_TTL_WIKI)
        return res
    r.raise_for_status()
    data = r.json()
    title = data.get("title", q)
    extract = data.get("extract", "")
    page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
    res = {
        "answer": f"{title}: {extract}",
        "citations": [page_url] if page_url else [f"https://en.wikipedia.org/wiki/{q}"],
        "retrieved_at": now,
        "quality": "verified",
    }
    cache_set(key, res, PROVIDER_CACHE_TTL_WIKI)
    return res


@router.get("/providers/restcountries")
def provider_restcountries(q: str | None = None):
    now = datetime.now(timezone.utc).isoformat()
    if not q or not q.strip():
        return {"answer": "No country name provided.",
                "citations": [], "retrieved_at": now, "quality": "verified"}

    key = cache_key("provider:restcountries", {"q": q.strip()})
    cached = cache_get(key)
    if cached:
        return cached

    try:
        r = requests.get(f"https://restcountries.com/v3.1/name/{q.strip()}", timeout=10)
        if r.status_code == 404:
            res = {"answer": f"No country found matching '{q}'.",
                   "citations": [f"https://restcountries.com/v3.1/name/{q}"],
                   "retrieved_at": now, "quality": "verified"}
            cache_set(key, res, PROVIDER_CACHE_TTL_RESTCOUNTRIES)
            return res
        r.raise_for_status()
        data = r.json()
        country = data[0] if data else {}
        name = country.get("name", {}).get("common", q)
        capital = ", ".join(country.get("capital", ["N/A"]))
        region = country.get("region", "N/A")
        population = country.get("population", "N/A")
        languages = ", ".join(country.get("languages", {}).values()) if country.get("languages") else "N/A"
        res = {
            "answer": (
                f"{name}: Capital: {capital}, Region: {region}, Population: {population:,} , "
                f"Languages: {languages}."
            ),
            "citations": [f"https://restcountries.com/v3.1/name/{q}"],
            "retrieved_at": now,
            "quality": "verified",
        }
        cache_set(key, res, PROVIDER_CACHE_TTL_RESTCOUNTRIES)
        return res
    except Exception as e:
        res = {"answer": f"Error fetching country data: {e}",
               "citations": [f"https://restcountries.com/v3.1/name/{q}"],
               "retrieved_at": now, "quality": "verified"}
        cache_set(key, res, PROVIDER_CACHE_TTL_RESTCOUNTRIES)
        return res


@router.get("/providers/exchangerate")
def provider_exchangerate(base: str | None = None, target: str | None = None):
    now = datetime.now(timezone.utc).isoformat()
    if not base or not base.strip():
        return {"answer": "No base currency provided.",
                "citations": [], "retrieved_at": now, "quality": "verified"}

    base = base.strip().upper()
    target = target.strip().upper() if isinstance(target, str) and target.strip() else None
    key = cache_key("provider:exchangerate", {"base": base, "target": target})
    cached = cache_get(key)
    if cached:
        return cached

    try:
        r = requests.get(f"https://open.er-api.com/v6/latest/{base}", timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("result") != "success":
            res = {"answer": f"Exchange rate API returned non-success for '{base}'.",
                   "citations": [], "retrieved_at": now, "quality": "verified"}
            cache_set(key, res, PROVIDER_CACHE_TTL_FX)
            return res
        rates = data.get("rates", {})
        if target:
            rate_strs = [f"{target}: {rates[target]}"] if target in rates and target != base else []
        else:
            symbols = sorted([c for c in rates.keys() if c != base])
            rate_strs = [f"{c}: {rates[c]}" for c in symbols[:10]]
        res = {
            "answer": (
                f"Exchange rates for 1 {base}: {', '.join(rate_strs[:6])}. "
                f"Last updated: {data.get('time_last_update_utc', 'N/A')}."
            ),
            "citations": [f"https://open.er-api.com/v6/latest/{base}"],
            "retrieved_at": now,
            "quality": "verified",
        }
        cache_set(key, res, PROVIDER_CACHE_TTL_FX)
        return res
    except Exception as e:
        res = {"answer": f"Error fetching exchange rates: {e}",
               "citations": [], "retrieved_at": now, "quality": "verified"}
        cache_set(key, res, PROVIDER_CACHE_TTL_FX)
        return res


@router.get("/providers/dictionary")
def provider_dictionary(word: str | None = None):
    now = datetime.now(timezone.utc).isoformat()
    if not word or not word.strip():
        return {"answer": "No word provided.",
                "citations": [], "retrieved_at": now, "quality": "verified"}

    word = word.strip().lower()
    key = cache_key("provider:dictionary", {"word": word})
    cached = cache_get(key)
    if cached:
        return cached

    try:
        r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=10)
        if r.status_code == 404:
            res = {"answer": f"No definition found for '{word}'.",
                   "citations": [], "retrieved_at": now, "quality": "verified"}
            cache_set(key, res, PROVIDER_CACHE_TTL_DICTIONARY)
            return res
        r.raise_for_status()
        data = r.json()
        entry = data[0] if data else {}
        defs = []
        for m in entry.get("meanings", [])[:3]:
            part = m.get("partOfSpeech", "")
            d = m.get("definitions", [{}])[0].get("definition", "")
            defs.append(f"({part}) {d}")
        res = {
            "answer": f"{word}: {'; '.join(defs)}",
            "citations": [f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"],
            "retrieved_at": now,
            "quality": "verified",
        }
        cache_set(key, res, PROVIDER_CACHE_TTL_DICTIONARY)
        return res
    except Exception as e:
        res = {"answer": f"Error fetching definition: {e}",
               "citations": [], "retrieved_at": now, "quality": "verified"}
        cache_set(key, res, PROVIDER_CACHE_TTL_DICTIONARY)
        return res


@router.get("/providers/openlibrary")
def provider_openlibrary(q: str | None = None):
    now = datetime.now(timezone.utc).isoformat()
    if not q or not q.strip():
        return {"answer": "No search query provided.",
                "citations": [], "retrieved_at": now, "quality": "verified"}

    key = cache_key("provider:openlibrary", {"q": q.strip()})
    cached = cache_get(key)
    if cached:
        return cached

    try:
        r = requests.get(
            "https://openlibrary.org/search.json",
            params={"q": q.strip(), "limit": 3},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        docs = data.get("docs", [])
        if not docs:
            res = {"answer": f"No books found for '{q}'.",
                   "citations": [], "retrieved_at": now, "quality": "verified"}
            cache_set(key, res, PROVIDER_CACHE_TTL_OPENLIB)
            return res
        results = []
        for doc in docs[:3]:
            title = doc.get("title", "Unknown")
            author = ", ".join(doc.get("author_name", ["Unknown"]))
            year = doc.get("first_publish_year", "N/A")
            results.append(f'"{title}" by {author} ({year})')
        res = {
            "answer": f"Books matching '{q}': {'; '.join(results)}.",
            "citations": [f"https://openlibrary.org/search?q={q}"],
            "retrieved_at": now,
            "quality": "verified",
        }
        cache_set(key, res, PROVIDER_CACHE_TTL_OPENLIB)
        return res
    except Exception as e:
        res = {"answer": f"Error searching books: {e}",
               "citations": [], "retrieved_at": now, "quality": "verified"}
        cache_set(key, res, PROVIDER_CACHE_TTL_OPENLIB)
        return res


@router.get("/providers/wikidata")
def provider_wikidata(q: str | None = None, limit: int = 3):
    now = datetime.now(timezone.utc).isoformat()
    if not q or not q.strip():
        return {"answer": "No search query provided.",
                "citations": [], "retrieved_at": now, "quality": "verified"}

    key = cache_key("provider:wikidata", {"q": q.strip(), "limit": limit})
    cached = cache_get(key)
    if cached:
        return cached

    params = {
        "action": "wbsearchentities",
        "search": q.strip(),
        "language": "en",
        "format": "json",
        "limit": max(1, min(int(limit), 5)),
    }
    try:
        r = requests.get(
            "https://www.wikidata.org/w/api.php",
            params=params,
            timeout=10,
            headers={"User-Agent": "Axiomeer/0.1"},
        )
        r.raise_for_status()
        data = r.json()
        results = data.get("search", [])
        if not results:
            res = {"answer": f"No Wikidata entities found for '{q}'.",
                   "citations": [], "retrieved_at": now, "quality": "verified"}
            cache_set(key, res, PROVIDER_CACHE_TTL_WIKIDATA)
            return res
        lines = []
        citations = []
        for item in results[:3]:
            label = item.get("label", "Unknown")
            desc = item.get("description", "")
            url = item.get("url", "")
            lines.append(f"{label} — {desc}".strip(" —"))
            if url:
                citations.append(url)
        res = {
            "answer": f"Wikidata results for '{q}': " + "; ".join(lines) + ".",
            "citations": citations,
            "retrieved_at": now,
            "quality": "verified",
        }
        cache_set(key, res, PROVIDER_CACHE_TTL_WIKIDATA)
        return res
    except Exception as e:
        res = {"answer": f"Error fetching Wikidata data: {e}",
               "citations": [], "retrieved_at": now, "quality": "verified"}
        cache_set(key, res, PROVIDER_CACHE_TTL_WIKIDATA)
        return res


@router.get("/providers/wikipedia_dumps")
def provider_wikipedia_dumps(lang: str | None = None):
    now = datetime.now(timezone.utc).isoformat()
    if not lang or not lang.strip():
        return {"answer": "No language code provided (e.g., en, es, fr).",
                "citations": [], "retrieved_at": now, "quality": "verified"}

    key = cache_key("provider:wikipedia_dumps", {"lang": lang.strip().lower()})
    cached = cache_get(key)
    if cached:
        return cached

    lang = lang.strip().lower()
    dump_url = f"https://dumps.wikimedia.org/{lang}wiki/latest/{lang}wiki-latest-pages-articles.xml.bz2"
    res = {
        "answer": f"Latest Wikipedia dump for '{lang}': {dump_url}",
        "citations": [dump_url, "https://dumps.wikimedia.org/legal.html"],
        "retrieved_at": now,
        "quality": "verified",
    }
    cache_set(key, res, PROVIDER_CACHE_TTL_WIKIDUMPS)
    return res
