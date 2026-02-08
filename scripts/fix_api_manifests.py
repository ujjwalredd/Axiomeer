#!/usr/bin/env python3
"""
Fix API manifests by adding test_inputs for APIs that require parameters
"""

import json
from pathlib import Path

# Define test inputs for each failing API
TEST_INPUTS = {
    # Financial
    "coinbase_prices": {"currency_pair": "BTC-USD"},
    "coingecko_crypto": {"coin_id": "bitcoin"},

    # Entertainment
    "pokemon_data": {"name": "pikachu"},

    # Science
    "newton_math": {"operation": "simplify", "expression": "2x+3x"},
    "periodic_table": {"element": "H"},
    "sunrise_sunset": {"lat": "36.7201600", "lng": "-4.4203400"},

    # Fun
    "numbers_trivia": {"number": "42"},

    # Language
    "language_detect": {"text": "Hello world"},
    "word_definition": {"word": "hello"},
    "gender_from_name": {"name": "John"},
    "word_synonyms": {"word": "happy"},

    # Utilities
    "color_info": {"hex": "ff0000"},
    "base64_decode": {"data": "SGVsbG8gV29ybGQ="},
    "postman_echo": {"message": "test"},
    "base64_encode": {"text": "Hello World"},

    # Knowledge
    "archive_org": {"query": "python programming"},
    "nationalize_predict_nationality": {"name": "Michael"},
    "dbpedia_sparql": {"query": "SELECT ?name WHERE { <http://dbpedia.org/resource/Python_(programming_language)> rdfs:label ?name } LIMIT 1"},
    "agify_predict_age": {"name": "Michael"},
    "zippopotam_lookup": {"country": "us", "postal_code": "90210"},
    "semantic_scholar": {"query": "machine learning"},
    "wikidata_sparql": {"query": "SELECT ?item WHERE { ?item wdt:P31 wd:Q5 } LIMIT 1"},

    # Food
    "fruityvice_nutrition": {"fruit": "banana"},

    # Geographic
    "geonames": {"q": "London"},
    "nominatim_geocoding": {"query": "London"},

    # Government Data
    "data_gov": {"query": "education"},
    "eu_open_data": {"query": "climate"},
    "uk_police_data": {"lat": "51.5074", "lng": "-0.1278"},

    # Media
    "unsplash_photos": {"query": "nature"},
    "genius_lyrics": {"query": "Bohemian Rhapsody"},
    "musicbrainz": {"query": "Beatles"},
    "pexels_media": {"query": "mountains"},

    # AI Models (all need Ollama running)
    "ollama_mistral_7b": {"prompt": "What is Python?"},
    "ollama_llama3_8b": {"prompt": "What is Python?"},
    "ollama_codellama_13b": {"prompt": "Write a hello world function"},
    "ollama_deepseek_coder": {"prompt": "Write a hello world function"},
}

def update_manifest(manifest_path: Path, api_id: str, test_inputs: dict):
    """Update a manifest file with test_inputs"""
    try:
        with open(manifest_path) as f:
            data = json.load(f)

        # Add test_inputs if not already present
        if 'test_inputs' not in data:
            data['test_inputs'] = test_inputs

        # Write back
        with open(manifest_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✓ Updated {api_id}")
        return True
    except Exception as e:
        print(f"✗ Failed to update {api_id}: {e}")
        return False

def main():
    manifests_dir = Path("manifests/categories")
    updated = 0
    failed = 0

    print("Fixing API manifests with test inputs...\n")

    for api_id, test_inputs in TEST_INPUTS.items():
        # Find the manifest file
        found = False
        for manifest_file in manifests_dir.rglob(f"{api_id}.json"):
            if update_manifest(manifest_file, api_id, test_inputs):
                updated += 1
                found = True
            else:
                failed += 1
            break

        if not found:
            print(f"⚠ Manifest not found for {api_id}")

    print(f"\n{'='*60}")
    print(f"Updated: {updated}")
    print(f"Failed: {failed}")
    print(f"{'='*60}")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
