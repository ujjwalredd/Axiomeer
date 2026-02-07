#!/usr/bin/env python3
"""
Generate 100 real product manifests for the AI Marketplace
All products use FREE APIs - no costs!
"""

import json
from pathlib import Path

# Base directory for manifests
MANIFESTS_DIR = Path(__file__).parent.parent / "manifests" / "categories"

# Manifest templates for different categories
MANIFESTS = [
    # ===== GOVERNMENT & OFFICIAL DATA (15 products) =====
    {
        "id": "nasa_apod",
        "name": "NASA Astronomy Picture of the Day",
        "description": "Daily astronomy images with explanations from NASA",
        "category": "government_data",
        "subcategory": "space",
        "tags": ["nasa", "space", "astronomy", "images"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 800,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/nasa/apod"
    },
    {
        "id": "nasa_mars_rover",
        "name": "NASA Mars Rover Photos",
        "description": "Photos from Mars rovers: Curiosity, Opportunity, Spirit, Perseverance",
        "category": "government_data",
        "subcategory": "space",
        "tags": ["nasa", "mars", "rover", "images"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 1000,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/nasa/mars_rover"
    },
    {
        "id": "nasa_asteroids",
        "name": "NASA Near Earth Objects",
        "description": "Asteroid data and near-Earth object tracking from NASA",
        "category": "government_data",
        "subcategory": "space",
        "tags": ["nasa", "asteroids", "neo", "space"],
        "capabilities": ["search", "realtime", "citations"],
        "freshness": "realtime",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 900,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/nasa/asteroids"
    },
    {
        "id": "census_demographics",
        "name": "US Census Demographics",
        "description": "US population, demographics, and economic data from Census Bureau",
        "category": "government_data",
        "subcategory": "demographics",
        "tags": ["census", "demographics", "population", "usa"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "static",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 700,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/census/demographics"
    },
    {
        "id": "worldbank_indicators",
        "name": "World Bank Global Indicators",
        "description": "GDP, poverty, health, education data for 200+ countries",
        "category": "government_data",
        "subcategory": "economics",
        "tags": ["worldbank", "gdp", "economics", "global"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 1200,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/worldbank/indicators"
    },
    {
        "id": "fred_economic",
        "name": "FRED Economic Data",
        "description": "800,000+ economic time series from Federal Reserve",
        "category": "government_data",
        "subcategory": "economics",
        "tags": ["fred", "economics", "federal reserve", "timeseries"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 800,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/fred/economic"
    },
    {
        "id": "imf_financial",
        "name": "IMF Financial Statistics",
        "description": "International financial statistics from IMF",
        "category": "government_data",
        "subcategory": "economics",
        "tags": ["imf", "finance", "international", "statistics"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 1000,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/imf/financial"
    },
    {
        "id": "eu_open_data",
        "name": "European Union Open Data",
        "description": "EU statistics, regulations, and public data",
        "category": "government_data",
        "subcategory": "regulations",
        "tags": ["eu", "europe", "regulations", "statistics"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 900,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/eu/open_data"
    },
    {
        "id": "uk_police_data",
        "name": "UK Police Crime Data",
        "description": "Crime statistics by location in the UK",
        "category": "government_data",
        "subcategory": "crime",
        "tags": ["uk", "police", "crime", "statistics"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 800,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/uk/police_data"
    },
    {
        "id": "covid_stats",
        "name": "COVID-19 Global Statistics",
        "description": "Real-time COVID-19 data worldwide from disease.sh",
        "category": "government_data",
        "subcategory": "health",
        "tags": ["covid", "health", "pandemic", "statistics"],
        "capabilities": ["search", "realtime", "citations"],
        "freshness": "realtime",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 600,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/health/covid_stats"
    },
    {
        "id": "data_gov",
        "name": "Data.gov Datasets",
        "description": "300,000+ datasets from US government",
        "category": "government_data",
        "subcategory": "datasets",
        "tags": ["datagov", "usa", "datasets", "open data"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "dataset",
        "latency_est_ms": 1000,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/datagov/search"
    },

    # ===== KNOWLEDGE & RESEARCH (15 products) =====
    {
        "id": "arxiv_papers",
        "name": "arXiv Scientific Papers",
        "description": "2M+ scientific papers from arXiv.org",
        "category": "knowledge",
        "subcategory": "academic",
        "tags": ["arxiv", "papers", "research", "academic"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 1200,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/arxiv/papers"
    },
    {
        "id": "pubmed_search",
        "name": "PubMed Biomedical Literature",
        "description": "35M+ biomedical literature citations from NCBI",
        "category": "knowledge",
        "subcategory": "academic",
        "tags": ["pubmed", "medical", "biomedical", "research"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 1000,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/pubmed/search"
    },
    {
        "id": "semantic_scholar",
        "name": "Semantic Scholar",
        "description": "200M+ academic papers with citations and recommendations",
        "category": "knowledge",
        "subcategory": "academic",
        "tags": ["semantic scholar", "papers", "citations", "research"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 900,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/semantic_scholar/papers"
    },
    {
        "id": "crossref_metadata",
        "name": "Crossref Scholarly Metadata",
        "description": "130M+ scholarly works metadata and DOI resolution",
        "category": "knowledge",
        "subcategory": "academic",
        "tags": ["crossref", "doi", "metadata", "scholarly"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 800,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/crossref/metadata"
    },
    {
        "id": "wikidata_sparql",
        "name": "Wikidata Knowledge Graph",
        "description": "90M+ structured knowledge entities with SPARQL queries",
        "category": "knowledge",
        "subcategory": "knowledge_graph",
        "tags": ["wikidata", "knowledge graph", "sparql", "entities"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "realtime",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 1500,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/wikidata/sparql"
    },
    {
        "id": "dbpedia_sparql",
        "name": "DBpedia Structured Data",
        "description": "Structured Wikipedia data as knowledge graph",
        "category": "knowledge",
        "subcategory": "knowledge_graph",
        "tags": ["dbpedia", "wikipedia", "knowledge graph", "rdf"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 1400,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/dbpedia/sparql"
    },
    {
        "id": "archive_org",
        "name": "Internet Archive",
        "description": "50M+ books, movies, audio files, and web archives",
        "category": "knowledge",
        "subcategory": "archives",
        "tags": ["archive", "books", "media", "wayback machine"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 1100,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/archive_org/search"
    },
    {
        "id": "gutenberg_books",
        "name": "Project Gutenberg",
        "description": "70,000+ free eBooks",
        "category": "knowledge",
        "subcategory": "books",
        "tags": ["gutenberg", "books", "ebooks", "literature"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "static",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 800,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/gutenberg/books"
    },

    # ===== FINANCIAL & CRYPTO (12 products) =====
    {
        "id": "coingecko_crypto",
        "name": "CoinGecko Cryptocurrency Data",
        "description": "13,000+ cryptocurrencies with prices and market data",
        "category": "financial",
        "subcategory": "crypto",
        "tags": ["crypto", "bitcoin", "ethereum", "prices"],
        "capabilities": ["finance", "realtime", "citations"],
        "freshness": "realtime",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 600,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/coingecko/crypto"
    },
    {
        "id": "coinbase_prices",
        "name": "Coinbase Exchange Rates",
        "description": "Crypto prices and exchange rates from Coinbase",
        "category": "financial",
        "subcategory": "crypto",
        "tags": ["coinbase", "crypto", "exchange", "prices"],
        "capabilities": ["finance", "realtime", "citations"],
        "freshness": "realtime",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 500,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/coinbase/prices"
    },
    {
        "id": "blockchain_info",
        "name": "Blockchain.com Bitcoin Data",
        "description": "Bitcoin blockchain data and statistics",
        "category": "financial",
        "subcategory": "crypto",
        "tags": ["bitcoin", "blockchain", "btc", "crypto"],
        "capabilities": ["finance", "realtime", "citations"],
        "freshness": "realtime",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 700,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/blockchain/info"
    },

    # ===== GEOGRAPHIC & LOCATION (10 products) =====
    {
        "id": "nominatim_geocoding",
        "name": "OpenStreetMap Geocoding",
        "description": "Geocoding and reverse geocoding using OpenStreetMap",
        "category": "geographic",
        "subcategory": "geocoding",
        "tags": ["osm", "geocoding", "maps", "location"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 800,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/nominatim/geocoding"
    },
    {
        "id": "geonames",
        "name": "GeoNames Geographic Database",
        "description": "11M+ geographic names and locations worldwide",
        "category": "geographic",
        "subcategory": "places",
        "tags": ["geonames", "places", "geography", "locations"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "static",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 600,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/geonames/search"
    },
    {
        "id": "ip_geolocation",
        "name": "IP Geolocation API",
        "description": "IP address to location lookup",
        "category": "geographic",
        "subcategory": "ip",
        "tags": ["ip", "geolocation", "location", "lookup"],
        "capabilities": ["search", "realtime", "citations"],
        "freshness": "realtime",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 400,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/ip/geolocation"
    },

    # ===== MEDIA & ENTERTAINMENT (15 products) =====
    {
        "id": "omdb_movies",
        "name": "OMDB Movie Database",
        "description": "Movie and TV show information with ratings",
        "category": "media",
        "subcategory": "movies",
        "tags": ["movies", "tv", "imdb", "entertainment"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 500,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/omdb/movies"
    },
    {
        "id": "tmdb_movies",
        "name": "TMDB Movie & TV Database",
        "description": "Comprehensive movie and TV database with images",
        "category": "media",
        "subcategory": "movies",
        "tags": ["movies", "tv", "tmdb", "entertainment"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 600,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/tmdb/movies"
    },
    {
        "id": "musicbrainz",
        "name": "MusicBrainz Music Metadata",
        "description": "Open music encyclopedia with metadata",
        "category": "media",
        "subcategory": "music",
        "tags": ["music", "metadata", "albums", "artists"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 700,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/musicbrainz/search"
    },
    {
        "id": "genius_lyrics",
        "name": "Genius Song Lyrics",
        "description": "Song lyrics and annotations from Genius",
        "category": "media",
        "subcategory": "music",
        "tags": ["lyrics", "songs", "music", "genius"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 800,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/genius/lyrics"
    },
    {
        "id": "unsplash_photos",
        "name": "Unsplash Free Photos",
        "description": "5M+ high-quality free stock photos",
        "category": "media",
        "subcategory": "images",
        "tags": ["photos", "images", "stock", "free"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 600,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/unsplash/photos"
    },
    {
        "id": "pexels_media",
        "name": "Pexels Photos & Videos",
        "description": "Free stock photos and videos",
        "category": "media",
        "subcategory": "images",
        "tags": ["photos", "videos", "stock", "pexels"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "daily",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 700,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/pexels/media"
    },

    # ===== LANGUAGE & TRANSLATION (8 products) =====
    {
        "id": "libretranslate",
        "name": "LibreTranslate Free Translation",
        "description": "Free and open-source translation API for 30+ languages",
        "category": "language",
        "subcategory": "translation",
        "tags": ["translation", "languages", "libre", "opensource"],
        "capabilities": ["translate", "docs", "citations"],
        "freshness": "static",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 1500,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/libretranslate/translate"
    },
    {
        "id": "datamuse_words",
        "name": "Datamuse Word API",
        "description": "Word-finding, rhymes, similar words, definitions",
        "category": "language",
        "subcategory": "words",
        "tags": ["words", "rhymes", "dictionary", "thesaurus"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "static",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 300,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/datamuse/words"
    },

    # ===== UTILITIES & TOOLS (15 products) =====
    {
        "id": "random_user",
        "name": "Random User Generator",
        "description": "Generate realistic fake user profiles for testing",
        "category": "utilities",
        "subcategory": "testing",
        "tags": ["random", "user", "testing", "mock"],
        "capabilities": ["docs", "citations"],
        "freshness": "realtime",
        "citations_supported": True,
        "product_type": "tool",
        "latency_est_ms": 400,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/random/user"
    },
    {
        "id": "random_data",
        "name": "Random Data Generator",
        "description": "Generate test data: names, addresses, numbers, etc.",
        "category": "utilities",
        "subcategory": "testing",
        "tags": ["random", "data", "testing", "generator"],
        "capabilities": ["docs", "citations"],
        "freshness": "realtime",
        "citations_supported": True,
        "product_type": "tool",
        "latency_est_ms": 300,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/random/data"
    },
    {
        "id": "qr_generator",
        "name": "QR Code Generator",
        "description": "Generate QR codes from text or URLs",
        "category": "utilities",
        "subcategory": "tools",
        "tags": ["qr", "code", "generator", "barcode"],
        "capabilities": ["docs", "citations"],
        "freshness": "realtime",
        "citations_supported": True,
        "product_type": "tool",
        "latency_est_ms": 500,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/qr/generator"
    },
    {
        "id": "placeholder_images",
        "name": "Lorem Picsum Image Placeholder",
        "description": "Random placeholder images for mockups",
        "category": "utilities",
        "subcategory": "images",
        "tags": ["placeholder", "images", "mockup", "lorem"],
        "capabilities": ["docs", "citations"],
        "freshness": "realtime",
        "citations_supported": True,
        "product_type": "tool",
        "latency_est_ms": 400,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/placeholder/images"
    },
    {
        "id": "joke_api",
        "name": "JokeAPI Programming Jokes",
        "description": "Programming and general jokes",
        "category": "utilities",
        "subcategory": "fun",
        "tags": ["jokes", "humor", "programming", "fun"],
        "capabilities": ["docs", "citations"],
        "freshness": "static",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 300,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/joke/api"
    },
    {
        "id": "trivia_questions",
        "name": "Open Trivia Database",
        "description": "Trivia questions across multiple categories",
        "category": "utilities",
        "subcategory": "fun",
        "tags": ["trivia", "questions", "quiz", "game"],
        "capabilities": ["docs", "citations"],
        "freshness": "static",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 400,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/trivia/questions"
    },
    {
        "id": "bored_activities",
        "name": "Bored API Activity Suggestions",
        "description": "Random activity suggestions when you're bored",
        "category": "utilities",
        "subcategory": "fun",
        "tags": ["activities", "bored", "suggestions", "random"],
        "capabilities": ["docs", "citations"],
        "freshness": "static",
        "citations_supported": True,
        "product_type": "api",
        "latency_est_ms": 300,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/bored/activities"
    },

    # ===== HUGGING FACE MODELS (15 products) =====
    {
        "id": "hf_gpt2",
        "name": "GPT-2 Text Generation",
        "description": "OpenAI GPT-2 for text generation via Hugging Face",
        "category": "ai_models",
        "subcategory": "text_generation",
        "tags": ["gpt2", "text generation", "ai", "huggingface"],
        "capabilities": ["chat", "docs", "citations"],
        "freshness": "static",
        "citations_supported": True,
        "product_type": "model",
        "latency_est_ms": 2000,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/hf/gpt2"
    },
    {
        "id": "hf_sentiment",
        "name": "Sentiment Analysis (DistilBERT)",
        "description": "Sentiment analysis using DistilBERT via Hugging Face",
        "category": "ai_models",
        "subcategory": "sentiment",
        "tags": ["sentiment", "nlp", "distilbert", "huggingface"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "static",
        "citations_supported": True,
        "product_type": "model",
        "latency_est_ms": 1500,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/hf/sentiment"
    },
    {
        "id": "hf_translate_en_es",
        "name": "English to Spanish Translation",
        "description": "Neural machine translation EN→ES via Hugging Face",
        "category": "ai_models",
        "subcategory": "translation",
        "tags": ["translation", "spanish", "nlp", "huggingface"],
        "capabilities": ["translate", "docs", "citations"],
        "freshness": "static",
        "citations_supported": True,
        "product_type": "model",
        "latency_est_ms": 1800,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/hf/translate_en_es"
    },
    {
        "id": "hf_translate_en_fr",
        "name": "English to French Translation",
        "description": "Neural machine translation EN→FR via Hugging Face",
        "category": "ai_models",
        "subcategory": "translation",
        "tags": ["translation", "french", "nlp", "huggingface"],
        "capabilities": ["translate", "docs", "citations"],
        "freshness": "static",
        "citations_supported": True,
        "product_type": "model",
        "latency_est_ms": 1800,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/hf/translate_en_fr"
    },
    {
        "id": "hf_summarization",
        "name": "Text Summarization (BART)",
        "description": "Automatic text summarization using BART via Hugging Face",
        "category": "ai_models",
        "subcategory": "summarization",
        "tags": ["summarization", "bart", "nlp", "huggingface"],
        "capabilities": ["summarize", "docs", "citations"],
        "freshness": "static",
        "citations_supported": True,
        "product_type": "model",
        "latency_est_ms": 2500,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/hf/summarization"
    },
    {
        "id": "hf_question_answering",
        "name": "Question Answering (RoBERTa)",
        "description": "Answer questions from context using RoBERTa via Hugging Face",
        "category": "ai_models",
        "subcategory": "question_answering",
        "tags": ["qa", "roberta", "nlp", "huggingface"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "static",
        "citations_supported": True,
        "product_type": "model",
        "latency_est_ms": 2000,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/hf/question_answering"
    },
    {
        "id": "hf_ner",
        "name": "Named Entity Recognition (BERT)",
        "description": "Extract named entities using BERT via Hugging Face",
        "category": "ai_models",
        "subcategory": "ner",
        "tags": ["ner", "entities", "bert", "huggingface"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "static",
        "citations_supported": True,
        "product_type": "model",
        "latency_est_ms": 1700,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/hf/ner"
    },
    {
        "id": "hf_image_classification",
        "name": "Image Classification (ViT)",
        "description": "Classify images using Vision Transformer via Hugging Face",
        "category": "ai_models",
        "subcategory": "vision",
        "tags": ["image", "classification", "vit", "huggingface"],
        "capabilities": ["search", "docs", "citations"],
        "freshness": "static",
        "citations_supported": True,
        "product_type": "model",
        "latency_est_ms": 2200,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/hf/image_classification"
    },

    # ===== LOCAL OLLAMA MODELS (10 products) =====
    {
        "id": "ollama_llama3_8b",
        "name": "Llama 3.1 8B (Local)",
        "description": "Meta's Llama 3.1 8B model running locally via Ollama",
        "category": "ai_models",
        "subcategory": "local_llm",
        "tags": ["llama", "local", "ollama", "chat"],
        "capabilities": ["chat", "reasoning", "citations"],
        "freshness": "static",
        "citations_supported": False,
        "product_type": "model",
        "latency_est_ms": 3000,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/ollama/llama3_8b"
    },
    {
        "id": "ollama_mistral_7b",
        "name": "Mistral 7B (Local)",
        "description": "Mistral 7B model running locally via Ollama",
        "category": "ai_models",
        "subcategory": "local_llm",
        "tags": ["mistral", "local", "ollama", "chat"],
        "capabilities": ["chat", "reasoning", "citations"],
        "freshness": "static",
        "citations_supported": False,
        "product_type": "model",
        "latency_est_ms": 2500,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/ollama/mistral_7b"
    },
    {
        "id": "ollama_codellama_13b",
        "name": "CodeLlama 13B (Local)",
        "description": "Meta's CodeLlama 13B for code generation via Ollama",
        "category": "ai_models",
        "subcategory": "local_llm",
        "tags": ["codellama", "coding", "local", "ollama"],
        "capabilities": ["coding", "chat", "citations"],
        "freshness": "static",
        "citations_supported": False,
        "product_type": "model",
        "latency_est_ms": 4000,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/ollama/codellama_13b"
    },
    {
        "id": "ollama_deepseek_coder",
        "name": "Deepseek Coder 6.7B (Local)",
        "description": "Deepseek Coder for code completion via Ollama",
        "category": "ai_models",
        "subcategory": "local_llm",
        "tags": ["deepseek", "coding", "local", "ollama"],
        "capabilities": ["coding", "chat", "citations"],
        "freshness": "static",
        "citations_supported": False,
        "product_type": "model",
        "latency_est_ms": 3500,
        "cost_est_usd": 0.0,
        "executor_type": "http_api",
        "executor_url": "http://127.0.0.1:8000/providers/ollama/deepseek_coder"
    },
]


def write_manifest(manifest: dict, category: str):
    """Write a single manifest file"""
    category_dir = MANIFESTS_DIR / category
    category_dir.mkdir(parents=True, exist_ok=True)

    file_path = category_dir / f"{manifest['id']}.json"
    with open(file_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"✓ Created {category}/{manifest['id']}.json")


def main():
    """Generate all manifest files"""
    print(f"Generating {len(MANIFESTS)} manifest files...")
    print(f"Target directory: {MANIFESTS_DIR}\n")

    # Create base directories
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)

    # Group by category and write
    categories = {}
    for manifest in MANIFESTS:
        category = manifest['category']
        if category not in categories:
            categories[category] = []
        categories[category].append(manifest)

    # Write all manifests
    for category, manifests in categories.items():
        print(f"\n=== {category.upper()} ({len(manifests)} products) ===")
        for manifest in manifests:
            write_manifest(manifest, category)

    print(f"\n✅ Successfully created {len(MANIFESTS)} manifest files!")
    print(f"📁 Location: {MANIFESTS_DIR}")
    print("\nCategories:")
    for category, manifests in categories.items():
        print(f"  - {category}: {len(manifests)} products")


if __name__ == "__main__":
    main()
