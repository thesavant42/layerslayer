# layerslayer.py
#  Layerslayer main CLI with batch modes, CLI args, and logging
#  Complete filesystem enumeration using streaming decompression

import os
import sys
import argparse
from fetcher import (
    get_manifest,
    download_layer_blob,
    peek_layer_blob,
    peek_layer_blob_complete,
    peek_layer_blob_partial,
    layerslayer as layerslayer_bulk,
    fetch_build_steps,
    LayerPeekResult,
)
from utils import (
    parse_image_ref,
    registry_base_url,
    auth_headers,
    human_readable_size,
    load_token,
    save_token,
)

class Tee:
    """Duplicate stdout/stderr to a file and the console."""
    def __init__(self, *files):
        self.files = files
    def write(self, data):
        for f in self.files:
            f.write(data)
    def flush(self):
        for f in self.files:
            f.flush()


def format_entry_line(entry, show_permissions=True):
    """
    Format a TarEntry for display, similar to ls -la output.
    
    Args:
        entry: TarEntry object with rich metadata
        show_permissions: Whether to show full ls -la style output
    
    Returns:
        Formatted string for display
    """
    if show_permissions:
        # Full ls -la style: drwxr-xr-x  0  0  2024-01-15 10:30  filename
        size_str = human_readable_size(entry.size).rjust(8)
        if entry.is_symlink and entry.linkname:
            name_display = f"{entry.name} -> {entry.linkname}"
        else:
            name_display = entry.name + ("/" if entry.is_dir else "")
        return f"  {entry.mode}  {entry.uid:4d} {entry.gid:4d}  {size_str}  {entry.mtime}  {name_display}"
    else:
        # Simple format
        if entry.is_dir:
            return f"  [DIR]  {entry.name}/"
        elif entry.is_symlink:
            return f"  [LINK] {entry.name} -> {entry.linkname}"
        else:
            size_str = human_readable_size(entry.size)
            return f"  [FILE] {entry.name} ({size_str})"


def display_peek_result(result: LayerPeekResult, layer_size: int, verbose: bool = False):
    """
    Display the results of a layer peek operation.
    
    Args:
        result: LayerPeekResult from peek functions
        layer_size: Full layer size in bytes (for comparison)
        verbose: Whether to show detailed stats
    """
    if result.error:
        print(f"  [!] Error: {result.error}")
        return
    
    # Show efficiency stats
    if verbose or result.bytes_downloaded > 0:
        pct = (result.bytes_downloaded / layer_size * 100) if layer_size > 0 else 0
        print(f"\n  [Stats] Downloaded: {human_readable_size(result.bytes_downloaded)} "
              f"of {human_readable_size(layer_size)} ({pct:.2f}%)")
        if result.partial:
            print(f"  [Stats] Files found: {result.entries_found} (partial)")
        else:
            print(f"  [Stats] Files found: {result.entries_found} (complete)")
    
    print("\n  Layer contents:\n")
    
    for entry in result.entries:
        print(format_entry_line(entry, show_permissions=True))


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
    # Peek mode options
    p.add_argument(
        "--partial",
        action="store_true",
        help="Use partial streaming peek (faster, but incomplete listing)",
    )
    p.add_argument(
        "--peek-bytes", "-b",
        type=int,
        default=262144,
        help="Bytes to fetch for partial peek (default: 262144 = 256KB)",
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
    return p.parse_args()


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
        if args.partial:
            print(f"\n[*] Peeking into all layers (partial, {args.peek_bytes} bytes):")
        else:
            print(f"\n[*] Peeking into all layers (complete enumeration):")
        
        for idx, layer in enumerate(layers):
            layer_size = layer.get("size", 0)
            print(f"\n[Layer {idx}] {layer['digest']}")
            print(f"           Size: {human_readable_size(layer_size)}")
            
            if args.partial:
                # Partial streaming peek (faster, incomplete)
                result = peek_layer_blob_partial(
                    image_ref, 
                    layer["digest"], 
                    token,
                    initial_bytes=args.peek_bytes,
                )
            else:
                # Complete enumeration (downloads full layer)
                result = peek_layer_blob_complete(
                    image_ref, 
                    layer["digest"], 
                    layer_size,
                    token,
                )
            display_peek_result(result, layer_size, verbose=True)
        return

    # --- save-all mode ---
    if args.save_all:
        print("\n[*] Downloading all layers:")
        for idx, layer in enumerate(layers):
            print(f"Downloading Layer [{idx}] {layer['digest']} ...")
            download_layer_blob(image_ref, layer["digest"], layer["size"], token)
        return

    # --- default interactive mode ---
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

    for idx in indices:
        layer = layers[idx]
        layer_size = layer.get("size", 0)
        print(f"\n[Layer {idx}] {layer['digest']}")
        print(f"           Size: {human_readable_size(layer_size)}")
        
        if args.partial:
            # Partial streaming peek
            result = peek_layer_blob_partial(
                image_ref, 
                layer["digest"], 
                token,
                initial_bytes=args.peek_bytes,
            )
        else:
            # Complete enumeration (default)
            result = peek_layer_blob_complete(
                image_ref, 
                layer["digest"], 
                layer_size,
                token,
            )
        display_peek_result(result, layer_size, verbose=True)
        
        if input("Download this layer? (y/N) ").strip().lower() == "y":
            download_layer_blob(image_ref, layer["digest"], layer["size"], token)

if __name__ == "__main__":
    main()
