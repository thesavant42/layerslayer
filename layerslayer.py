# layerslayer.py
# 🛡️ Layerslayer main CLI

import os
import sys
from fetcher_patched import (
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
        print("🔑 No token found; proceeding anonymously.")

    # — Unpack whatever get_manifest returns (tuple of (json, token)) —
    result = get_manifest(image_ref, token)
    if isinstance(result, tuple):
        manifest_index, token = result
    else:
        manifest_index = result

    # — Handle multi-arch vs single-arch manifests —
    if "manifests" in manifest_index and manifest_index["manifests"]:
        platforms = manifest_index["manifests"]
        print("\nAvailable platforms:")
        for i, m in enumerate(platforms):
            plat = m["platform"]
            print(f" [{i}] {plat['os']}/{plat['architecture']}")
        choice = int(input("Select a platform [0]: ") or 0)
        digest = platforms[choice]["digest"]

        # fetch the chosen platform’s manifest (unpack again if needed)
        result = get_manifest(image_ref, token, specific_digest=digest)
        if isinstance(result, tuple):
            full_manifest, token = result
        else:
            full_manifest = result
    else:
        full_manifest = manifest_index
        print(f"\nSingle-arch image detected; using manifest directly")

    # — Fetch and display build steps —
    steps = fetch_build_steps(image_ref, full_manifest["config"]["digest"], token)
    print("\nBuild steps:")
    for idx, cmd in enumerate(steps):
        print(f" [{idx}] {cmd}")

    # — List layers —
    layers = full_manifest["layers"]
    print("\nLayers:")
    for idx, layer in enumerate(layers):
        size = human_readable_size(layer["size"])
        print(f" [{idx}] {layer['digest']} - {size}")

    # — Peek/download selection —
    sel = input("\nLayers to peek (comma-separated INDEX or ALL) [default: ALL]: ").strip()
    if not sel or sel.upper() == "ALL":
        indices = list(range(len(layers)))
    else:
        indices = [int(i) for i in sel.split(",")]

    for idx in indices:
        layer = layers[idx]
        print(f"\n⦿ Layer [{idx}] {layer['digest']}")
        peek_layer_blob(image_ref, layer["digest"], token)
        if input("Download this layer? (y/N) ").strip().lower() == "y":
            download_layer_blob(image_ref, layer["digest"], layer["size"], token)

if __name__ == "__main__":
    main()
