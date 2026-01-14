# parser.py
# Parses manifest and config data
#
# EWhat's the origin of this file? And the module it imports?


from fetcher import get_manifest_by_digest

def parse_index(index_json, image_ref, token=None):
    """Handles an OCI image index with multiple architectures."""
    print("\nAvailable Platforms:")
    platforms = index_json.get('manifests', [])
    for i, platform in enumerate(platforms):
        plat = platform.get('platform', {})
        print(f"[{i}] {plat.get('os', 'unknown')}/{plat.get('architecture', 'unknown')}")

    choice = int(input("\nSelect platform index: "))
    chosen = platforms[choice]
    digest = chosen['digest']
    return get_manifest_by_digest(image_ref, digest, token=token)

def parse_manifest(manifest_json):
    """Parses a manifest to list its layers."""
    layers = manifest_json.get('layers', [])
    layer_info = []
    print("\nLayers:")
    for idx, layer in enumerate(layers):
        size = layer.get('size', 0)
        digest = layer.get('digest')
        print(f"[{idx}] {digest} - {size/1024:.1f} KB")
        layer_info.append({
            'digest': digest,
            'size': size
        })
    return layer_info
