#!/usr/bin/env python3
"""
Comprehensive API Health Check Script
Tests all 91 APIs and reports success/failure status
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any
import requests
from tabulate import tabulate
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def load_all_manifests() -> List[Dict[str, Any]]:
    """Load all API manifest files"""
    manifests = []
    manifests_dir = Path("manifests/categories")

    for manifest_file in manifests_dir.rglob("*.json"):
        try:
            with open(manifest_file) as f:
                data = json.load(f)
                data['_manifest_path'] = str(manifest_file)
                manifests.append(data)
        except Exception as e:
            print(f"{Colors.RED}Error loading {manifest_file}: {e}{Colors.END}")

    return manifests


def test_api(api_data: Dict[str, Any], base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """
    Test a single API endpoint

    Returns:
        {
            'success': bool,
            'status_code': int,
            'error': str,
            'response_time_ms': float,
            'response_sample': str
        }
    """
    api_id = api_data.get('id', 'unknown')

    # Use test_inputs from manifest if available, otherwise use generic inputs
    test_inputs = api_data.get('test_inputs', {})

    # Prepare test request
    test_payload = {
        "app_id": api_id,
        "task": "test query",
        "inputs": test_inputs,
        "require_citations": False
    }

    # Ollama models (13B+) can take 60+ seconds on first run
    timeout_sec = 90 if api_data.get('category') == 'ai_models' else 30

    try:
        start_time = time.time()
        response = requests.post(
            f"{base_url}/execute",
            json=test_payload,
            timeout=timeout_sec,
            headers={"Content-Type": "application/json"}
        )
        elapsed_ms = (time.time() - start_time) * 1000

        if response.status_code == 200:
            data = response.json()

            # Check if execution was successful
            if data.get('status') == 'error':
                return {
                    'success': False,
                    'status_code': 200,
                    'error': data.get('error', {}).get('message', 'Unknown error'),
                    'error_type': data.get('error', {}).get('type', 'unknown'),
                    'response_time_ms': elapsed_ms,
                    'response_sample': ''
                }

            # Check if ok=false (validation errors)
            if not data.get('ok', True):
                errors = data.get('validation_errors', ['Unknown validation error'])
                return {
                    'success': False,
                    'status_code': 200,
                    'error': errors[0] if errors else 'Validation failed',
                    'error_type': 'validation_error',
                    'response_time_ms': elapsed_ms,
                    'response_sample': ''
                }

            # Extract answer sample (handle None output)
            output = data.get('output')
            if output is None:
                return {
                    'success': False,
                    'status_code': 200,
                    'error': 'API returned null output',
                    'error_type': 'null_output',
                    'response_time_ms': elapsed_ms,
                    'response_sample': ''
                }

            answer = output.get('answer', '') if isinstance(output, dict) else str(output)
            sample = answer[:100] + '...' if len(answer) > 100 else answer

            return {
                'success': True,
                'status_code': 200,
                'error': '',
                'error_type': '',
                'response_time_ms': elapsed_ms,
                'response_sample': sample
            }
        else:
            return {
                'success': False,
                'status_code': response.status_code,
                'error': f"HTTP {response.status_code}: {response.text[:200]}",
                'error_type': 'http_error',
                'response_time_ms': elapsed_ms,
                'response_sample': ''
            }

    except requests.exceptions.Timeout:
        return {
            'success': False,
            'status_code': 0,
            'error': 'Request timeout (30s)',
            'error_type': 'timeout',
            'response_time_ms': 30000,
            'response_sample': ''
        }
    except requests.exceptions.ConnectionError:
        return {
            'success': False,
            'status_code': 0,
            'error': 'Connection failed - is the server running?',
            'error_type': 'connection_error',
            'response_time_ms': 0,
            'response_sample': ''
        }
    except Exception as e:
        return {
            'success': False,
            'status_code': 0,
            'error': f'Exception: {str(e)}',
            'error_type': 'exception',
            'response_time_ms': 0,
            'response_sample': ''
        }


def main():
    print(f"{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}AXIOMEER PRODUCTION READINESS - API HEALTH CHECK{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")

    # Load all manifests
    print(f"{Colors.BLUE}Loading API manifests...{Colors.END}")
    manifests = load_all_manifests()
    print(f"Found {len(manifests)} APIs to test\n")

    # Test each API
    results = []
    success_count = 0
    failure_count = 0
    error_types = defaultdict(int)
    category_stats = defaultdict(lambda: {'total': 0, 'passed': 0})

    print(f"{Colors.BLUE}Testing APIs...{Colors.END}\n")

    for i, api_data in enumerate(manifests, 1):
        api_id = api_data.get('id', 'unknown')
        api_name = api_data.get('name', api_id)
        category = api_data.get('category', 'unknown')

        print(f"[{i}/{len(manifests)}] Testing {api_id}...", end=" ", flush=True)

        result = test_api(api_data)
        result['api_id'] = api_id
        result['api_name'] = api_name
        result['category'] = category
        results.append(result)

        # Update stats
        category_stats[category]['total'] += 1
        if result['success']:
            success_count += 1
            category_stats[category]['passed'] += 1
            print(f"{Colors.GREEN}✓ PASS{Colors.END} ({result['response_time_ms']:.0f}ms)")
        else:
            failure_count += 1
            error_types[result['error_type']] += 1
            print(f"{Colors.RED}✗ FAIL{Colors.END} - {result['error'][:60]}")

    # Print summary
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}SUMMARY{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")

    pass_rate = (success_count / len(manifests) * 100) if manifests else 0

    print(f"Total APIs: {len(manifests)}")
    print(f"{Colors.GREEN}Passed: {success_count} ({pass_rate:.1f}%){Colors.END}")
    print(f"{Colors.RED}Failed: {failure_count} ({100-pass_rate:.1f}%){Colors.END}\n")

    # Category breakdown
    print(f"{Colors.BOLD}Category Breakdown:{Colors.END}\n")
    category_table = []
    for category, stats in sorted(category_stats.items()):
        cat_pass_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
        status = f"{Colors.GREEN}✓{Colors.END}" if cat_pass_rate == 100 else f"{Colors.RED}✗{Colors.END}"
        category_table.append([
            status,
            category,
            stats['passed'],
            stats['total'],
            f"{cat_pass_rate:.1f}%"
        ])

    print(tabulate(category_table, headers=['', 'Category', 'Pass', 'Total', 'Rate'], tablefmt='simple'))

    # Error type breakdown
    if error_types:
        print(f"\n{Colors.BOLD}Error Type Breakdown:{Colors.END}\n")
        error_table = []
        for error_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
            error_table.append([error_type, count])
        print(tabulate(error_table, headers=['Error Type', 'Count'], tablefmt='simple'))

    # Failed APIs detail
    if failure_count > 0:
        print(f"\n{Colors.BOLD}Failed APIs Detail:{Colors.END}\n")
        failed_table = []
        for result in results:
            if not result['success']:
                failed_table.append([
                    result['api_id'],
                    result['category'],
                    result['error_type'],
                    result['error'][:60]
                ])
        print(tabulate(failed_table, headers=['API ID', 'Category', 'Error Type', 'Error Message'], tablefmt='simple'))

    # Production readiness assessment
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}PRODUCTION READINESS ASSESSMENT{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")

    if pass_rate == 100:
        print(f"{Colors.GREEN}✓ ALL APIS PASSING - PRODUCTION READY{Colors.END}")
        return 0
    elif pass_rate >= 90:
        print(f"{Colors.YELLOW}⚠ {failure_count} APIs failing ({100-pass_rate:.1f}%) - NEEDS ATTENTION{Colors.END}")
        print(f"{Colors.YELLOW}Fix failing APIs before production deployment{Colors.END}")
        return 1
    else:
        print(f"{Colors.RED}✗ {failure_count} APIs failing ({100-pass_rate:.1f}%) - NOT PRODUCTION READY{Colors.END}")
        print(f"{Colors.RED}Critical issues must be resolved before deployment{Colors.END}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
