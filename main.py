#--- below here is candidates for main.py
#  Layerslayer main CLI with batch modes, CLI args, and logging
#  Complete filesystem enumeration using streaming decompression
import os
import sys
import argparse

from app.modules.keepers.downloaders import get_manifest, download_layer_blob, fetch_build_steps
from app.modules.finders.peekers import peek_layer_blob, peek_layer_blob_complete
from app.modules.keepers.layerSlayerResults import layerslayer as layerslayer_bulk, LayerPeekResult
from app.modules.keepers import storage
from app.modules.formatters import (
    parse_image_ref,
    registry_base_url,
    human_readable_size,
)
from app.modules.auth.auth import (
    auth_headers,
    load_token,
    save_token,
)
from app.modules.keepers.carver import carve_file, CarveResult
from app.modules.keepers.layerslayer import Tee, format_entry_line, display_peek_result


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
        "--peek-all",
        action="store_true",
        help="Peek into all layers and exit (no download prompts)",
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
    # TODO change ./carved to apps/loot/
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
    
    args = p.parse_args()
    # Show help if no mode selected
    if not any([args.peek_all, args.save_all, args.bulk_peek, args.carve_file, args.interactive]):
        p.print_help()
        sys.exit(0)
    return args


def main():
    args = parse_args()

    # set up logging/tee if requested
    if args.log_file:
        log_f = open(args.log_file, "w", encoding="utf-8")
        sys.stdout = Tee(sys.stdout, log_f)
        sys.stderr = Tee(sys.stderr, log_f)

    print(" Welcome to Layerslayer \n")

    # choose image from CLI or prompt
    if args.image_ref:
        image_ref = args.image_ref
    else:
        image_ref = input(
            "Enter image (user/repo:tag) [default: moby/buildkit:latest]: "
        ).strip() or "moby/buildkit:latest"

    # --- carve mode: extract a single file and exit ---
    if args.carve_file:
        print(f"[*] Carve mode: extracting {args.carve_file} from {image_ref}\n")
        result = carve_file(
            image_ref=image_ref,
            target_path=args.carve_file,
            output_dir=args.output_dir,
            verbose=not args.quiet,
        )
        if result.found:
            sys.exit(0)
        else:
            if result.error:
                print(f"[!] Error: {result.error}")
            sys.exit(1)

    token = load_token("token.txt")
    if token:
        print(" Loaded token from token.txt")
        print(" Using loaded token.")
    else:
        print(" No token found; proceeding anonymously.")

    # --- Unpack whatever get_manifest returns (tuple of (json, token)) ---
    result = get_manifest(image_ref, token)
    if isinstance(result, tuple):
        manifest_index, token = result
    else:
        manifest_index = result

    # --- Handle multi-arch vs single-arch manifests ---
    if manifest_index.get("manifests"):
        platforms = manifest_index["manifests"]
        print("\nAvailable platforms:")
        for i, m in enumerate(platforms):
            plat = m["platform"]
            print(f" [{i}] {plat['os']}/{plat['architecture']}")
        choice = int(input("Select a platform [0]: ") or 0)
        digest = platforms[choice]["digest"]
        # fetch the chosen platform's manifest (unpack again if needed)
        result = get_manifest(image_ref, token, specific_digest=digest)
        if isinstance(result, tuple):
            full_manifest, token = result
        else:
            full_manifest = result
    else:
        full_manifest = manifest_index
        print(f"\nSingle-arch image detected; using manifest directly")

    # --- Fetch and display build steps ---
    steps = fetch_build_steps(image_ref, full_manifest["config"]["digest"], token)
    print("\nBuild steps:")
    for idx, cmd in enumerate(steps):
        print(f" [{idx}] {cmd}")

    layers = full_manifest["layers"]

    # --- bulk-peek mode: peek all layers and show combined filesystem ---
    if args.bulk_peek:
        print(f"\n[*] Bulk peeking all {len(layers)} layers (complete enumeration)...")
        
        def progress(msg, current, total):
            print(f"  [{current+1}/{total}] {msg}")
        
        bulk_result = layerslayer_bulk(
            image_ref=image_ref,
            layers=layers,
            token=token,
            progress_callback=progress,
        )
        
        print(f"\n[*] Bulk peek complete:")
        print(f"    Layers peeked: {bulk_result.layers_peeked}")
        print(f"    Total downloaded: {human_readable_size(bulk_result.total_bytes_downloaded)}")
        print(f"    Total files found: {bulk_result.total_entries}")
        
        print("\n  Combined filesystem:\n")
        for entry in bulk_result.all_entries:
            print(format_entry_line(entry, show_permissions=not args.simple_output))
        
        return

    # --- peek-all mode: enumerate ALL files in each layer ---
    if args.peek_all:
        print(f"\n[*] Peeking into all layers (complete enumeration):")
        
        # Initialize database for storage
        conn = storage.init_database()
        
        try:
            for idx, layer in enumerate(layers):
                layer_size = layer.get("size", 0)
                print(f"\n[Layer {idx}] {layer['digest']}")
                print(f"           Size: {human_readable_size(layer_size)}")
                
                # Complete enumeration (downloads full layer)
                result = peek_layer_blob_complete(
                    image_ref,
                    layer["digest"],
                    layer_size,
                    token,
                )
                display_peek_result(result, layer_size, verbose=True)
                
                # Save layer result to JSON and SQLite
                storage.save_layer_result(result, image_ref, idx, layer_size, conn)
        finally:
            conn.close()
        return

    # --- save-all mode ---
    if args.save_all:
        print("\n[*] Downloading all layers:")
        for idx, layer in enumerate(layers):
            print(f"Downloading Layer [{idx}] {layer['digest']} ...")
            download_layer_blob(image_ref, layer["digest"], layer["size"], token)
        return

    # --- interactive mode (requires --interactive flag) ---
    if not args.interactive:
        return
    
    print("\nLayers:")
    for idx, layer in enumerate(layers):
        size = human_readable_size(layer["size"])
        print(f" [{idx}] {layer['digest']} - {size}")

    sel = input(
        "\nLayers to peek (comma-separated INDEX or ALL) [default: ALL]: "
    ).strip()
    if not sel or sel.upper() == "ALL":
        indices = list(range(len(layers)))
    else:
        indices = [int(i) for i in sel.split(",")]

    # Initialize database for storage
    conn = storage.init_database()
    
    try:
        for idx in indices:
            layer = layers[idx]
            layer_size = layer.get("size", 0)
            print(f"\n[Layer {idx}] {layer['digest']}")
            print(f"           Size: {human_readable_size(layer_size)}")
            
            # Complete enumeration (default)
            result = peek_layer_blob_complete(
                image_ref,
                layer["digest"],
                layer_size,
                token,
            )
            display_peek_result(result, layer_size, verbose=True)
            
            # Save layer result to JSON and SQLite
            storage.save_layer_result(result, image_ref, idx, layer_size, conn)
            
            if input("Download this layer? (y/N) ").strip().lower() == "y":
                download_layer_blob(image_ref, layer["digest"], layer["size"], token)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
