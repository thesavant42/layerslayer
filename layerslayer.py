# layerslayer.py
# 🛡️ Layerslayer main CLI

import os
import sys
from fetcher import (
    get_manifest,
    download_layer_blob,
    peek_layer_blob,
    fetch_build_steps,
)
from utils import (
    parse_image_ref,
    registry_base_url,
    auth_headers,
    human_readable_size,
    load_token,
    save_token,
)

def main():
    print("🛡️ Welcome to Layerslayer 🛡️\n")

    image_ref = input("Enter image (user/repo:tag) [default: moby/buildkit:latest]: ").strip()
    if not image_ref:
        image_ref = "moby/buildkit:latest"

    token = load_token("token.txt")
    if token:
        print("🔑 Loaded token from token.txt")
        print("🔑 Using loaded token.")
    else:
        print("⚠️ No token.txt found. Proceeding without user token.")

    manifest_data = get_manifest(image_ref, token=token)

    platforms = manifest_data.get("manifests", [])
    print("\nAvailable Platforms:")
    for idx, platform in enumerate(platforms):
        plat = platform.get("platform", {})
        print(f"[{idx}] {plat.get('os', 'unknown')}/{plat.get('architecture', 'unknown')}")

    platform_index = input("\nSelect platform index [default: 0]: ").strip()
    if not platform_index:
        platform_index = 0
    else:
        platform_index = int(platform_index)

    selected_manifest = platforms[platform_index]
    digest = selected_manifest["digest"]

    full_manifest = get_manifest(image_ref, token=token, specific_digest=digest)
    config_digest = full_manifest["config"]["digest"]

    # Fetch and display build steps
    build_steps = fetch_build_steps(image_ref, config_digest, token=token)

    if build_steps:
        print("\n🛠️  Build Steps (Dockerfile Commands):")
        print("----------------------------------------")
        for idx, step in enumerate(build_steps):
            print(f"Step {idx}: {step}")
        print("----------------------------------------\n")

    layers = full_manifest.get("layers", [])
    print("Layers:")
    for idx, layer in enumerate(layers):
        size = human_readable_size(layer.get("size", 0))
        print(f"[{idx}] {layer['digest']} - {size}")

    layer_input = input("\nSelect layer indexes to peek (e.g., 0,2,3) or ALL [default: 0]: ").strip()

    if not layer_input:
        selected_indexes = [0]
    elif layer_input.upper() == "ALL":
        selected_indexes = list(range(len(layers)))
    else:
        selected_indexes = [int(x.strip()) for x in layer_input.split(",")]

    for idx in selected_indexes:
        layer = layers[idx]
        digest = layer["digest"]
        size = layer.get("size", 0)

        print("\n🔍 Peeking into layer:")
        peek_layer_blob(image_ref, digest, token=token)

        download_decision = input("\nWould you like to download this layer? (y/N): ").strip().lower()
        if download_decision == "y":
            download_layer_blob(image_ref, digest, size, token=token)
        else:
            print("🛑 Skipping download.")

if __name__ == "__main__":
    main()
