# layerslayer.py
# Entry point for the Layerslayer tool (Peek-first, Build Steps shown)

from fetcher import (
    get_manifest,
    get_manifest_by_digest,
    download_layer_blob,
    peek_layer_blob,
    fetch_build_steps,
    load_cached_token
)
from parser import parse_manifest, parse_index
from utils import ensure_download_dir, select_from_list, load_token

def main():
    print("🛡️ Welcome to Layerslayer 🛡️\n")

    image_ref = input("Enter image (user/repo:tag): ").strip()

    # Try to load token.txt or cached pull token
    token = load_token()

    if not token:
        token = load_cached_token()

    if token:
        print("🔑 Using loaded token.")
    else:
        print("⚡ No token provided, proceeding with anonymous pull (may work for public images).")

    # Fetch the manifest
    manifest_data = get_manifest(image_ref, token=token)

    # Handle multi-platform or single platform manifest
    if manifest_data.get('mediaType', '').endswith('index.v1+json'):
        chosen_manifest = parse_index(manifest_data, image_ref, token)
    else:
        chosen_manifest = manifest_data

    # Fetch and show build steps before doing anything else
    config_digest = chosen_manifest['config']['digest']
    fetch_build_steps(image_ref, config_digest, token=token)

    # Parse and display layers
    layers_info = parse_manifest(chosen_manifest)

    # Setup download directory
    download_dir = ensure_download_dir(image_ref)

    # Let user select one or more layers
    selected = select_from_list(layers_info)

    for layer in selected:
        # Always peek first
        peek_layer_blob(image_ref, layer['digest'], token=token)

        # After peeking, offer to download
        decision = input("\nWould you like to download this layer? (y/n): ").strip().lower()
        if decision == 'y':
            download_layer_blob(image_ref, layer['digest'], token=token, output_dir=download_dir)
        else:
            print("🛑 Skipping download.\n")

if __name__ == "__main__":
    main()
