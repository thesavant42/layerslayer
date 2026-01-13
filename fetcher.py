# fetcher.py
#  Layerslayer registry fetch helpers with resilient token handling
#  Includes streaming layer peek using HTTP Range requests

import os
import zlib
import requests
import tarfile
import io
from dataclasses import dataclass, field
from typing import Optional, Callable, Generator

from utils import (
    parse_image_ref,
    registry_base_url,
    human_readable_size,
    save_token,
)
from tar_parser import TarEntry, parse_tar_header

# Persistent session to reuse headers & TCP connections for registry calls
session = requests.Session()
session.headers.update({
    "Accept": "application/vnd.docker.distribution.manifest.v2+json"
})


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


# =============================================================================
# Token Management
# =============================================================================

def fetch_pull_token(user, repo):
    """
    Retrieve a Docker Hub pull token (anonymous or authenticated).
    Bypasses the shared session so no extra headers confuse the auth endpoint.
    """
    auth_url = (
        f"https://auth.docker.io/token"
        f"?service=registry.docker.io&scope=repository:{user}/{repo}:pull"
    )
    try:
        # Use plain requests.get() here—no Accept or stale Auth headers
        resp = requests.get(auth_url)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f" Warning: pull-token endpoint error: {e}")
        return None

    token = resp.json().get("token")
    if not token:
        print(" Warning: token endpoint returned no token")
        return None

    save_token(token, filename="token_pull.txt")
    print(" Saved pull token to token_pull.txt.")
    # Now inject the fresh token into our session for all registry calls
    session.headers["Authorization"] = f"Bearer {token}"
    return token


# =============================================================================
# Manifest & Config Fetching
# =============================================================================

def get_manifest(image_ref, token=None, specific_digest=None):
    """
    Fetch either a multi-arch manifest list or a single-arch manifest.
    On 401, attempts one token refresh; if still 401, exits with a friendly message.
    """
    user, repo, tag = parse_image_ref(image_ref)
    ref = specific_digest or tag
    url = f"{registry_base_url(user, repo)}/manifests/{ref}"

    # If caller provided a token, set it before the request
    if token:
        session.headers["Authorization"] = f"Bearer {token}"

    resp = session.get(url)
    if resp.status_code == 401:
        print(" Unauthorized. Fetching fresh pull token...")
        new_token = fetch_pull_token(user, repo)
        if new_token:
            resp = session.get(url)
        else:
            print(" Proceeding without refreshed token.")

    if resp.status_code == 401:
        # Final unauthorized → clean exit
        print(f"X Error: Unauthorized fetching manifest for {image_ref}.")
        print("   - Ensure the image exists and token.txt (if used) is valid.")
        raise SystemExit(1)

    resp.raise_for_status()
    return resp.json()


def fetch_build_steps(image_ref, config_digest, token=None):
    """
    Download the image config blob and parse Dockerfile 'created_by' history.
    """
    user, repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url(user, repo)}/blobs/{config_digest}"

    resp = session.get(url)
    if resp.status_code == 401:
        print(" Unauthorized. Fetching fresh pull token...")
        new_token = fetch_pull_token(user, repo)
        if new_token:
            resp = session.get(url)
        else:
            print(" Proceeding without refreshed token.")

    resp.raise_for_status()
    config = resp.json()

    steps = []
    for entry in config.get("history", []):
        step = entry.get("created_by", "").strip()
        if entry.get("empty_layer", False):
            step += " (metadata only)"
        steps.append(step)
    return steps


# =============================================================================
# Layer Download (Full)
# =============================================================================

def download_layer_blob(image_ref, digest, size, token=None):
    """
    Stream a layer blob to disk as a .tar.gz file.
    """
    user, repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url(user, repo)}/blobs/{digest}"

    resp = session.get(url, stream=True)
    if resp.status_code == 401:
        print(" Unauthorized. Fetching fresh pull token...")
        new_token = fetch_pull_token(user, repo)
        if new_token:
            resp = session.get(url, stream=True)
        else:
            print(" Proceeding without refreshed token.")

    resp.raise_for_status()

    user_repo = f"{user}_{repo}"
    output_dir = os.path.join("downloads", user_repo, "latest")
    os.makedirs(output_dir, exist_ok=True)

    filename = digest.replace(":", "_") + ".tar.gz"
    path = os.path.join(output_dir, filename)

    with open(path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    print(f"[+] Saved layer {digest} to {path}")


# =============================================================================
# Layer Peek (Legacy - Full Download)
# =============================================================================

def peek_layer_blob(image_ref, digest, token=None):
    """
    Download a layer blob into memory and list its contents.
    DEPRECATED: Use peek_layer_blob_partial() for streaming peek.
    """
    user, repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url(user, repo)}/blobs/{digest}"

    resp = session.get(url, stream=True)
    if resp.status_code == 401:
        print(" Unauthorized. Fetching fresh pull token...")
        new_token = fetch_pull_token(user, repo)
        if new_token:
            resp = session.get(url, stream=True)
        else:
            print(" Proceeding without refreshed token.")

    resp.raise_for_status()

    tar_bytes = io.BytesIO(resp.content)
    with tarfile.open(fileobj=tar_bytes, mode="r:gz") as tar:
        print("\n Layer contents:\n")
        for member in tar.getmembers():
            if member.isdir():
                print(f"  [DIR] {member.name}/")
            else:
                size = human_readable_size(member.size)
                print(f"  [FILE] {member.name} ({size})")


# =============================================================================
# Streaming Layer Peek (HTTP Range Requests)
# =============================================================================

def peek_layer_blob_partial(
    image_ref: str,
    digest: str,
    token: Optional[str] = None,
    initial_bytes: int = 65536,
) -> LayerPeekResult:
    """
    Fetch only first N bytes of a layer using HTTP Range request,
    decompress, and parse tar headers.
    
    Returns partial file listing - enough for a preview.
    Key insight: 64KB download can discover 40+ files from a 30MB layer.
    
    Args:
        image_ref: Image reference (e.g., "nginx:latest" or "library/nginx:latest")
        digest: Layer digest (e.g., "sha256:abc123...")
        token: Optional auth token, will fetch if not provided
        initial_bytes: How many bytes to fetch (default 64KB)
        
    Returns:
        LayerPeekResult with partial file listing
    """
    user, repo, _ = parse_image_ref(image_ref)
    
    # Get token if not provided
    if not token:
        token = fetch_pull_token(user, repo)
    
    url = f"{registry_base_url(user, repo)}/blobs/{digest}"
    
    # Build headers with Range request
    headers = {
        "Range": f"bytes=0-{initial_bytes - 1}",
        "Accept": "application/vnd.docker.distribution.manifest.v2+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        resp = requests.get(url, headers=headers, stream=True, timeout=30)
        
        # Handle auth retry
        if resp.status_code == 401:
            token = fetch_pull_token(user, repo)
            if token:
                headers["Authorization"] = f"Bearer {token}"
                resp = requests.get(url, headers=headers, stream=True, timeout=30)
        
        resp.raise_for_status()
        
        # Read the partial data
        compressed_data = resp.raw.read(initial_bytes)
        resp.close()
        
    except requests.RequestException as e:
        return LayerPeekResult(
            digest=digest,
            partial=True,
            bytes_downloaded=0,
            bytes_decompressed=0,
            entries_found=0,
            entries=[],
            error=str(e),
        )
    
    # Verify gzip magic (0x1f 0x8b)
    if len(compressed_data) < 2 or compressed_data[0:2] != b'\x1f\x8b':
        return LayerPeekResult(
            digest=digest,
            partial=True,
            bytes_downloaded=len(compressed_data),
            bytes_decompressed=0,
            entries_found=0,
            entries=[],
            error="Not a gzip file (missing magic bytes)",
        )
    
    # Decompress with zlib (handles partial streams)
    try:
        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)  # 16 = gzip format
        decompressed = decompressor.decompress(compressed_data)
    except zlib.error as e:
        return LayerPeekResult(
            digest=digest,
            partial=True,
            bytes_downloaded=len(compressed_data),
            bytes_decompressed=0,
            entries_found=0,
            entries=[],
            error=f"Decompression error: {e}",
        )
    
    if len(decompressed) < 512:
        return LayerPeekResult(
            digest=digest,
            partial=True,
            bytes_downloaded=len(compressed_data),
            bytes_decompressed=len(decompressed),
            entries_found=0,
            entries=[],
            error="Not enough decompressed data for tar header",
        )
    
    # Parse tar headers
    entries = []
    offset = 0
    
    while offset + 512 <= len(decompressed):
        entry, next_offset = parse_tar_header(decompressed, offset)
        if entry is None:
            break
        entries.append(entry)
        
        if next_offset <= offset or next_offset > len(decompressed):
            # Next header would be outside our buffer
            break
        offset = next_offset
    
    return LayerPeekResult(
        digest=digest,
        partial=True,
        bytes_downloaded=len(compressed_data),
        bytes_decompressed=len(decompressed),
        entries_found=len(entries),
        entries=entries,
    )


def peek_layer_blob_streaming(
    image_ref: str,
    digest: str,
    token: Optional[str] = None,
    initial_bytes: int = 65536,
) -> Generator[TarEntry, None, LayerPeekResult]:
    """
    Generator version that yields entries as they are parsed.
    
    This allows the UI to display entries progressively as they're discovered.
    
    Usage:
        gen = peek_layer_blob_streaming(image_ref, digest)
        for entry in gen:
            display(entry)  # Each entry as it's discovered
        # After exhausting generator, use gen.value for final stats
    
    Yields:
        TarEntry objects as they are parsed
        
    Returns:
        LayerPeekResult with final stats (accessible via generator.value)
    """
    user, repo, _ = parse_image_ref(image_ref)
    
    # Get token if not provided
    if not token:
        token = fetch_pull_token(user, repo)
    
    url = f"{registry_base_url(user, repo)}/blobs/{digest}"
    
    # Build headers with Range request
    headers = {
        "Range": f"bytes=0-{initial_bytes - 1}",
        "Accept": "application/vnd.docker.distribution.manifest.v2+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    error_msg = None
    compressed_data = b""
    decompressed = b""
    entries = []
    
    try:
        resp = requests.get(url, headers=headers, stream=True, timeout=30)
        
        # Handle auth retry
        if resp.status_code == 401:
            token = fetch_pull_token(user, repo)
            if token:
                headers["Authorization"] = f"Bearer {token}"
                resp = requests.get(url, headers=headers, stream=True, timeout=30)
        
        resp.raise_for_status()
        
        # Read the partial data
        compressed_data = resp.raw.read(initial_bytes)
        resp.close()
        
    except requests.RequestException as e:
        error_msg = str(e)
        return LayerPeekResult(
            digest=digest,
            partial=True,
            bytes_downloaded=0,
            bytes_decompressed=0,
            entries_found=0,
            entries=[],
            error=error_msg,
        )
    
    # Verify gzip magic (0x1f 0x8b)
    if len(compressed_data) < 2 or compressed_data[0:2] != b'\x1f\x8b':
        return LayerPeekResult(
            digest=digest,
            partial=True,
            bytes_downloaded=len(compressed_data),
            bytes_decompressed=0,
            entries_found=0,
            entries=[],
            error="Not a gzip file (missing magic bytes)",
        )
    
    # Decompress with zlib (handles partial streams)
    try:
        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        decompressed = decompressor.decompress(compressed_data)
    except zlib.error as e:
        return LayerPeekResult(
            digest=digest,
            partial=True,
            bytes_downloaded=len(compressed_data),
            bytes_decompressed=0,
            entries_found=0,
            entries=[],
            error=f"Decompression error: {e}",
        )
    
    if len(decompressed) < 512:
        return LayerPeekResult(
            digest=digest,
            partial=True,
            bytes_downloaded=len(compressed_data),
            bytes_decompressed=len(decompressed),
            entries_found=0,
            entries=[],
            error="Not enough decompressed data for tar header",
        )
    
    # Parse tar headers and yield entries as we go
    offset = 0
    
    while offset + 512 <= len(decompressed):
        entry, next_offset = parse_tar_header(decompressed, offset)
        if entry is None:
            break
        entries.append(entry)
        yield entry  # Stream the entry to caller
        
        if next_offset <= offset or next_offset > len(decompressed):
            break
        offset = next_offset
    
    # Return final stats
    return LayerPeekResult(
        digest=digest,
        partial=True,
        bytes_downloaded=len(compressed_data),
        bytes_decompressed=len(decompressed),
        entries_found=len(entries),
        entries=entries,
    )


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
    Peek ALL layers for an image and merge into virtual filesystem.
    
    - Fetches each layer via peek_layer_blob_partial()
    - Returns combined result with total bytes stats
    
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
    layer_digests = [
        layer.get("digest")
        for layer in layers
        if layer.get("digest")
    ]
    
    if not layer_digests:
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
    layers_from_cache = 0  # Not implemented yet, always 0
    
    for i, digest in enumerate(layer_digests):
        if progress_callback:
            progress_callback(f"Peeking layer {i+1}/{len(layer_digests)}", i, len(layer_digests))
        
        # Fetch layer peek
        result = peek_layer_blob_partial(
            image_ref=image_ref,
            digest=digest,
            token=token,
        )
        
        layer_results.append(result)
        total_bytes += result.bytes_downloaded
        
        if not result.error:
            all_entries.extend(result.entries)
    
    if progress_callback:
        progress_callback("Done", len(layer_digests), len(layer_digests))
    
    # Use the first layer's digest as image reference (or empty if none)
    image_digest = layer_digests[0] if layer_digests else ""
    
    return LayerSlayerResult(
        image_digest=image_digest,
        layers_peeked=len(layer_digests),
        layers_from_cache=layers_from_cache,
        total_bytes_downloaded=total_bytes,
        total_entries=len(all_entries),
        all_entries=all_entries,
        layer_results=layer_results,
    )
