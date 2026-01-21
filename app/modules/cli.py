# CLI argument parsing for Layerslayer
# Refactored from main.py to follow single responsibility principle

import argparse
import sys


def parse_args():
    p = argparse.ArgumentParser(
        description="Explore and download individual Docker image layers."
    )
    p.add_argument(
        "--target-image", "-t",
        dest="image_ref",
        help="Image (user/repo:tag) to inspect",
    )
    p.add_argument(
        "--peek-layer",
        dest="peek_layer",
        default=None,
        help="Peek layer(s): 'all' for all layers, or integer index for specific layer",
    )
    p.add_argument(
        "--save-all",
        action="store_true",
        help="Download all layers and exit (no peek listings)",
    )
    p.add_argument(
        "--log-file", "-l",
        dest="log_file",
        help="Path to save a complete log of output",
    )
    p.add_argument(
        "--simple-output",
        action="store_true",
        help="Use simple output format instead of ls -la style",
    )
    p.add_argument(
        "--bulk-peek",
        action="store_true",
        help="Peek all layers in bulk and show combined filesystem",
    )
    # File carving options
    p.add_argument(
        "--carve-file", "-f",
        dest="carve_file",
        help="Extract a specific file from the image (e.g., /etc/passwd)",
    )
    
    p.add_argument(
        "--output-dir", "-o",
        dest="output_dir",
        default="./apps/loot/",
        help="Output directory for carved files (default: ./carved)",
    )
    p.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress detailed progress output",
    )
    p.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Launch interactive mode with prompts",
    )
    p.add_argument(
        "--arch", "-a",
        dest="arch",
        type=int,
        default=None,
        help="Platform index for multi-arch images (e.g., 0 for first platform). "
             "Skips interactive platform selection.",
    )
    p.add_argument(
        "--force", "-F",
        action="store_true",
        help="Force overwrite of existing database entries without prompting, for non-interactive mode",
    )
    p.add_argument(
        "--hide-build",
        action="store_true",
        help="Hide build steps output (only show summary line)",
    )
    p.add_argument(
        "--api", "-A",
        action="store_true",
        help="Start the API server (uvicorn on 127.0.0.1:8000)",
    )
    
    args = p.parse_args()
    # Show help if no mode selected
    if not any([args.peek_layer, args.save_all, args.bulk_peek, args.carve_file, args.interactive, args.api]):
        p.print_help()
        sys.exit(0)
    return args
