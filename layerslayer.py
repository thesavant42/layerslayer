# layerslayer.py
#  Layerslayer main CLI with batch modes, CLI args, and logging

import os
import sys
import argparse
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

    # — Unpack whatever get_manifest returns (tuple of (json, token)) —
    result = get_manifest(image_ref, token)
    if isinstance(result, tuple):
        manifest_index, token = result
    else:
        manifest_index = result

    # — Handle multi-arch vs single-arch manifests —
    if manifest_index.get("manifests"):
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

    layers = full_manifest["layers"]

    # — peek-all mode? —
    if args.peek_all:
        print("\n📂 Peeking into all layers:")
        for idx, layer in enumerate(layers):
            print(f"\n⦿ Layer [{idx}] {layer['digest']}")
            peek_layer_blob(image_ref, layer["digest"], token)
        return

    # — save-all mode? —
    if args.save_all:
        print("\n Downloading all layers:")
        for idx, layer in enumerate(layers):
            print(f"Downloading Layer [{idx}] {layer['digest']} …")
            download_layer_blob(image_ref, layer["digest"], layer["size"], token)
        return

    # — default interactive mode —
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
        print(f"\n⦿ Layer [{idx}] {layer['digest']}")
        peek_layer_blob(image_ref, layer["digest"], token)
        if input("Download this layer? (y/N) ").strip().lower() == "y":
            download_layer_blob(image_ref, layer["digest"], layer["size"], token)

if __name__ == "__main__":
    main()
