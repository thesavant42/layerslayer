#--- below here is candidates for main.py
#  Layerslayer main CLI with batch modes, CLI args, and logging
#  Complete filesystem enumeration using streaming decompression
import os
import sys

from app.modules.keepers.downloaders import get_manifest, download_layer_blob, fetch_build_steps
from app.modules.finders.peekers import peek_layer_streaming
from app.modules.keepers.layerSlayerResults import layerslayer as layerslayer_bulk, LayerPeekResult
from app.modules.keepers import storage
from app.modules.formatters import (
    parse_image_ref,
    registry_base_url,
    human_readable_size,
)
from app.modules.auth import RegistryAuth
from app.modules.keepers.carver import carve_file, CarveResult
from app.modules.keepers.layerslayer import Tee, format_entry_line, display_peek_result
from app.modules.cli import parse_args


def main():
    args = parse_args()

    # --- API server mode ---
    if args.api:
        import uvicorn
        print("[*] Starting API server on http://127.0.0.1:8000/docs")
        uvicorn.run("app.modules.api.api:app", host="127.0.0.1", port=8000, reload=True)
        return

    # set up logging/tee if requested
    if args.log_file:
        log_f = open(args.log_file, "w", encoding="utf-8")
        sys.stdout = Tee(sys.stdout, log_f)
        sys.stderr = Tee(sys.stderr, log_f)

    #print(" Welcome to Layerslayer \n")

    # choose image from CLI or prompt
    if args.image_ref:
        image_ref = args.image_ref
    else:
        image_ref = input(
            "Enter image (user/repo:tag) [example: moby/buildkit:latest]: "
        ).strip() or "moby/buildkit:latest"

    # Parse image reference to get namespace/repo for auth
    user, repo, tag = parse_image_ref(image_ref)

    # --- carve mode: extract a single file and exit ---
    # Note: carve_file creates its own RegistryAuth internally
    if args.carve_file:
        layer_msg = f" from layer {args.carve_layer}" if args.carve_layer is not None else ""
        print(f"[*] Carve mode: extracting {args.carve_file} from {image_ref}{layer_msg}\n")
        result = carve_file(
            image_ref=image_ref,
            target_path=args.carve_file,
            output_dir=args.output_dir,
            verbose=not args.quiet,
            layer_index=args.carve_layer,
        )
        if result.found:
            sys.exit(0)
        else:
            if result.error:
                print(f"[!] Error: {result.error}")
            sys.exit(1)

    # Create centralized auth instance for all operations
    auth = RegistryAuth(user, repo)
    
    try:
        # --- Fetch manifest ---
        manifest_index = get_manifest(auth, image_ref)

        # --- Handle multi-arch vs single-arch manifests ---
        if manifest_index.get("manifests"):
            platforms = manifest_index["manifests"]
            print("\nAvailable platforms:")
            for i, m in enumerate(platforms):
                plat = m["platform"]
                print(f" [{i}] {plat['os']}/{plat['architecture']}")
            
            # Use --arch if provided, otherwise prompt interactively
            if args.arch is not None:
                if args.arch < 0 or args.arch >= len(platforms):
                    print(f"\n[!] Error: --arch {args.arch} is out of range. "
                          f"Valid indices: 0-{len(platforms) - 1}")
                    return
                choice = args.arch
                print(f"\nUsing platform index {choice} (from --arch)")
            else:
                choice = int(input("Select a platform [0]: ") or 0)
            
            digest = platforms[choice]["digest"]
            # fetch the chosen platform's manifest
            full_manifest = get_manifest(auth, image_ref, specific_digest=digest)
        else:
            full_manifest = manifest_index
            print(f"\nSingle-arch image detected; using manifest directly")

        # --- Fetch and display build steps ---
        steps = fetch_build_steps(auth, image_ref, full_manifest["config"]["digest"])
        if args.hide_build:
            print(f"\nBuild steps: hidden ({len(steps)} steps)")
        else:
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
                auth=auth,
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

        # --- peek-layer mode: enumerate files in specified layer(s) ---
        if args.peek_layer is not None:
            # Determine which layers to peek
            if args.peek_layer.lower() == "all":
                indices = list(range(len(layers)))
                print(f"\n[*] Peeking into all {len(layers)} layers (complete enumeration):")
            else:
                layer_index = int(args.peek_layer)
                if layer_index < 0 or layer_index >= len(layers):
                    print(f"\n[!] Error: layer index {layer_index} is out of range. "
                          f"Valid indices: 0-{len(layers) - 1}")
                    return
                indices = [layer_index]
                print(f"\n[*] Peeking into layer {layer_index}:")
            
            # Initialize database for storage
            conn = storage.init_database()
            
            try:
                for idx in indices:
                    layer = layers[idx]
                    layer_size = layer.get("size", 0)
                    print(f"\n[Layer {idx}] {layer['digest']}")
                    print(f"           Size: {human_readable_size(layer_size)}")
                    
                    # Complete enumeration using incremental streaming
                    result = peek_layer_streaming(
                        auth,
                        image_ref,
                        layer["digest"],
                        layer_size,
                    )
                    display_peek_result(result, layer_size, verbose=True)
                    
                    # Save layer result to JSON and SQLite
                    storage.save_layer_result(result, image_ref, idx, layer_size, conn, force_overwrite=args.force)
            finally:
                conn.close()
            return

        # --- save-all mode ---
        if args.save_all:
            print("\n[*] Downloading all layers:")
            for idx, layer in enumerate(layers):
                print(f"Downloading Layer [{idx}] {layer['digest']} ...")
                download_layer_blob(auth, image_ref, layer["digest"], layer["size"])
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
                
                # Complete enumeration using incremental streaming
                result = peek_layer_streaming(
                    auth,
                    image_ref,
                    layer["digest"],
                    layer_size,
                )
                display_peek_result(result, layer_size, verbose=True)
                
                # Save layer result to JSON and SQLite
                storage.save_layer_result(result, image_ref, idx, layer_size, conn, force_overwrite=args.force)
                
                if input("Download this layer? (y/N) ").strip().lower() == "y":
                    download_layer_blob(auth, image_ref, layer["digest"], layer["size"])
        finally:
            conn.close()
    
    finally:
        # Always invalidate auth session when done
        auth.invalidate()

if __name__ == "__main__":
    main()
