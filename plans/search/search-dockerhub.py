#!/usr/bin/env python3
"""Docker Hub Search CLI - Task 1"""

import argparse
import json
import sys
from datetime import datetime
import requests


def resolve(data, idx):
    """Resolve value at index, recursively resolving objects and arrays."""
    if isinstance(idx, int):
        if idx < 0:
            return None
        idx = data[idx]
    
    if isinstance(idx, dict):
        obj = {}
        for k, v in idx.items():
            if k.startswith('_'):
                key_name = data[int(k[1:])]
                obj[key_name] = resolve(data, v)
        return obj
    
    if isinstance(idx, list):
        return [resolve(data, i) for i in idx]
    
    return idx


def get_results(data):
    """Extract results from flat array structure."""
    for i, v in enumerate(data):
        if v == "searchResults":
            sr = resolve(data, data[i + 1])
            return sr.get('results', []), sr.get('total', 0)
    return [], 0


def format_date(iso_str):
    """Convert ISO date to MM-DD-YYYY format."""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        return dt.strftime('%m-%d-%Y')
    except (ValueError, AttributeError):
        return str(iso_str)


def print_results(results, total):
    """Print results as formatted table."""
    print(f"\nTotal: {total} results\n")
    print(f"{'SLUG':<40} {'FAV':<4} {'PULLS':<6} {'CREATED':<12} {'UPDATED':<12} DESCRIPTION")
    print("-" * 100)
    
    for r in results:
        slug = r.get('id', '')
        stars = r.get('star_count', 0)
        pulls = r.get('pull_count', '0')
        publisher = r.get('publisher', {})
        pub_name = publisher.get('name', '') if isinstance(publisher, dict) else ''
        created = format_date(r.get('created_at', ''))
        updated = format_date(r.get('updated_at', ''))
        desc = r.get('short_description', '')
        
        print(f"{slug:<40} {stars:<4} {pulls:<6} {created:<12} {updated:<12} {desc}")


def main():
    parser = argparse.ArgumentParser(description='Search Docker Hub')
    parser.add_argument('-q', '--query', help='Search query')
    parser.add_argument('--page', type=int, default=1, help='Page number')
    parser.add_argument('--sort', choices=['pull_count', 'updated_at'], help='Sort field')
    parser.add_argument('--order', choices=['asc', 'desc'], default='desc', help='Sort order')
    parser.add_argument('--file', help='Load from local JSON file (for testing)')
    args = parser.parse_args()
    
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        results, total = get_results(data)
        print_results(results, total)
    elif args.query:
        # Build Docker Hub search URL
        url = "https://hub.docker.com/search.data"
        params = {
            'q': args.query,
            'page': args.page,
            'order': args.order
        }
        if args.sort:
            params['sortby'] = args.sort
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            results, total = get_results(data)
            print_results(results, total)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching search results: {e}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error parsing response: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()

