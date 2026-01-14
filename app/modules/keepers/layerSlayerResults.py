

# Copiped from fetcher.py

# =============================================================================
# Data Classes for Streaming Peek Results
# =============================================================================

@dataclass
class LayerPeekResult:
    """Result of peeking into a layer blob."""
    digest: str
    partial: bool
    bytes_downloaded: int
    bytes_decompressed: int
    entries_found: int
    entries: list[TarEntry]
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "digest": self.digest,
            "partial": self.partial,
            "bytes_downloaded": self.bytes_downloaded,
            "bytes_decompressed": self.bytes_decompressed,
            "entries_found": self.entries_found,
            "entries": [e.to_dict() for e in self.entries],
            "error": self.error,
        }


@dataclass
class LayerSlayerResult:
    """Result of peeking into ALL layers of an image."""
    image_digest: str
    layers_peeked: int
    layers_from_cache: int
    total_bytes_downloaded: int
    total_entries: int
    all_entries: list[TarEntry]  # Merged from all layers
    layer_results: list[LayerPeekResult] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "image_digest": self.image_digest,
            "layers_peeked": self.layers_peeked,
            "layers_from_cache": self.layers_from_cache,
            "total_bytes_downloaded": self.total_bytes_downloaded,
            "total_entries": self.total_entries,
            "all_entries": [e.to_dict() for e in self.all_entries],
            "layer_results": [r.to_dict() for r in self.layer_results],
            "error": self.error,
        }

## Copied from fetcher.py

# =============================================================================
# Layer Slayer: Bulk Layer Peek
# =============================================================================

def layerslayer(
    image_ref: str,
    layers: list[dict],
    token: Optional[str] = None,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> LayerSlayerResult:
    """
    Peek ALL layers for an image with COMPLETE file enumeration.
    
    Downloads and decompresses each layer fully to enumerate every file.
    
    Args:
        image_ref: Image reference (e.g., "nginx:latest")
        layers: List of layer dicts from manifest["layers"]
        token: Optional auth token
        progress_callback: Optional callback(message, current, total)
        
    Returns:
        LayerSlayerResult with all layer entries and stats
    """
    user, repo, _ = parse_image_ref(image_ref)
    
    # Filter to layers with digests only
    layer_info = [
        (layer.get("digest"), layer.get("size", 0))
        for layer in layers
        if layer.get("digest")
    ]
    
    if not layer_info:
        return LayerSlayerResult(
            image_digest="",
            layers_peeked=0,
            layers_from_cache=0,
            total_bytes_downloaded=0,
            total_entries=0,
            all_entries=[],
            error="No layers with digests found",
        )
    
    # Get a token for all layer requests (reuse for efficiency)
    if not token:
        token = fetch_pull_token(user, repo)
    
    all_entries: list[TarEntry] = []
    layer_results: list[LayerPeekResult] = []
    total_bytes = 0
    layers_from_cache = 0
    
    for i, (digest, layer_size) in enumerate(layer_info):
        if progress_callback:
            progress_callback(f"Peeking layer {i+1}/{len(layer_info)}", i, len(layer_info))
        
        # Use COMPLETE enumeration - download full layer
        result = peek_layer_blob_complete(
            image_ref=image_ref,
            digest=digest,
            layer_size=layer_size,
            token=token,
        )
        
        layer_results.append(result)
        total_bytes += result.bytes_downloaded
        
        if not result.error:
            all_entries.extend(result.entries)
    
    if progress_callback:
        progress_callback("Done", len(layer_info), len(layer_info))
    
    # Use the first layer's digest as image reference (or empty if none)
    image_digest = layer_info[0][0] if layer_info else ""
    
    return LayerSlayerResult(
        image_digest=image_digest,
        layers_peeked=len(layer_info),
        layers_from_cache=layers_from_cache,
        total_bytes_downloaded=total_bytes,
        total_entries=len(all_entries),
        all_entries=all_entries,
        layer_results=layer_results,
    )
