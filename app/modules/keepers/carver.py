# carver.py
# Single-file extraction from Docker image layers using HTTP Range requests
# and incremental streaming decompression.
#
# Based on: https://github.com/thesavant42/dockerdorker/blob/main/app/modules/carve/carve-file-from-layer.py

import time
import zlib
import requests
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.modules.formatters import parse_image_ref, registry_base_url
from app.modules.finders.tar_parser import TarEntry, parse_tar_header
from app.modules.auth import RegistryAuth


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_CHUNK_SIZE = 65536  # 64KB chunks
DEFAULT_OUTPUT_DIR = "./carved"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ScanResult:
    """Result of scanning for a target file in tar data."""
    found: bool
    entry: Optional[TarEntry] = None
    content_offset: int = 0  # Offset in decompressed buffer where content starts
    content_size: int = 0
    entries_scanned: int = 0


@dataclass
class CarveResult:
    """Result of a file carving operation."""
    found: bool
    saved_path: Optional[str] = None
    target_file: str = ""
    bytes_downloaded: int = 0
    layer_size: int = 0
    efficiency_pct: float = 0.0
    elapsed_time: float = 0.0
    layer_digest: Optional[str] = None
    layers_searched: int = 0
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "found": self.found,
            "saved_path": self.saved_path,
            "target_file": self.target_file,
            "bytes_downloaded": self.bytes_downloaded,
            "layer_size": self.layer_size,
            "efficiency_pct": self.efficiency_pct,
            "elapsed_time": self.elapsed_time,
            "layer_digest": self.layer_digest,
            "layers_searched": self.layers_searched,
            "error": self.error,
        }


# =============================================================================
# Manifest Fetching
# =============================================================================

@dataclass
class LayerInfo:
    """Information about a layer from the manifest."""
    digest: str
    size: int
    media_type: str


def _fetch_manifest(auth: RegistryAuth, namespace: str, repo: str, tag: str) -> list[LayerInfo]:
    """
    Fetch image manifest and extract layer information.
    
    Args:
        auth: RegistryAuth instance for authenticated requests
        namespace: Docker Hub namespace
        repo: Repository name
        tag: Image tag
        
    Returns list of LayerInfo in order (base layer first).
    """
    url = f"{registry_base_url(namespace, repo)}/manifests/{tag}"
    
    try:
        resp = auth.request_with_retry("GET", url, timeout=30)
        resp.raise_for_status()
        manifest = resp.json()
    except requests.RequestException as e:
        print(f"  [!] Error fetching manifest: {e}")
        return []
    
    # Handle manifest list (multi-arch) - pick first amd64/linux
    media_type = manifest.get("mediaType", "")
    if "manifest.list" in media_type or "image.index" in media_type:
        manifests = manifest.get("manifests", [])
        # Find amd64/linux manifest
        target = None
        for m in manifests:
            platform = m.get("platform", {})
            if platform.get("architecture") == "amd64" and platform.get("os") == "linux":
                target = m
                break
        if not target and manifests:
            target = manifests[0]  # Fallback to first
        
        if target:
            # Fetch the actual manifest
            digest = target.get("digest")
            url = f"{registry_base_url(namespace, repo)}/manifests/{digest}"
            resp = auth.request_with_retry("GET", url, timeout=30)
            resp.raise_for_status()
            manifest = resp.json()
    
    # Extract layers
    layers = []
    for layer in manifest.get("layers", []):
        layers.append(LayerInfo(
            digest=layer.get("digest", ""),
            size=layer.get("size", 0),
            media_type=layer.get("mediaType", ""),
        ))
    
    return layers


# =============================================================================
# Incremental Gzip Decompressor
# =============================================================================

class IncrementalGzipDecompressor:
    """
    Decompresses gzip data incrementally, maintaining state across chunk feeds.
    """
    
    def __init__(self):
        # 16 + MAX_WBITS tells zlib to expect gzip format
        self.decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        self.buffer = b""
        self.bytes_decompressed = 0
        self.error: Optional[str] = None
    
    def feed(self, compressed_data: bytes) -> bytes:
        """
        Feed compressed data and return newly decompressed bytes.
        Also appends to internal buffer.
        """
        if not compressed_data:
            return b""
        
        try:
            decompressed = self.decompressor.decompress(compressed_data)
            self.buffer += decompressed
            self.bytes_decompressed += len(decompressed)
            return decompressed
        except zlib.error as e:
            self.error = str(e)
            return b""
    
    def get_buffer(self) -> bytes:
        """Return the full decompressed buffer."""
        return self.buffer


# =============================================================================
# Incremental Blob Reader
# =============================================================================

class IncrementalBlobReader:
    """
    Fetches blob data in chunks using HTTP Range requests.
    """
    
    def __init__(
        self,
        auth: RegistryAuth,
        namespace: str,
        repo: str,
        digest: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ):
        self.auth = auth
        self.url = f"{registry_base_url(namespace, repo)}/blobs/{digest}"
        self.chunk_size = chunk_size
        self.current_offset = 0
        self.bytes_downloaded = 0
        self.total_size = 0  # Set after first request
        self.exhausted = False
    
    def fetch_chunk(self) -> bytes:
        """
        Fetch the next chunk of data. Returns empty bytes if exhausted.
        """
        if self.exhausted:
            return b""
        
        end_offset = self.current_offset + self.chunk_size - 1
        
        # Get session and add Range header
        session = self.auth.get_session()
        headers = {"Range": f"bytes={self.current_offset}-{end_offset}"}
        
        try:
            resp = session.get(self.url, headers=headers, stream=True, timeout=30)
            
            # Check response - 416 means range not satisfiable (past end)
            if resp.status_code == 416:
                self.exhausted = True
                return b""
            
            # Handle 401 by refreshing token and retrying
            if resp.status_code == 401:
                self.auth._token = None
                session = self.auth.get_session()
                resp = session.get(self.url, headers=headers, stream=True, timeout=30)
            
            resp.raise_for_status()
            
            # Get total size from Content-Range header
            content_range = resp.headers.get("Content-Range", "")
            if "/" in content_range:
                self.total_size = int(content_range.split("/")[-1])
            
            data = resp.raw.read(self.chunk_size)
            resp.close()
            
            if not data:
                self.exhausted = True
                return b""
            
            self.bytes_downloaded += len(data)
            self.current_offset += len(data)
            
            # Check if we've reached the end
            if self.total_size and self.current_offset >= self.total_size:
                self.exhausted = True
            
            return data
            
        except requests.RequestException as e:
            print(f"  [!] Error fetching chunk: {e}")
            self.exhausted = True
            return b""


# =============================================================================
# Tar Scanner
# =============================================================================

class TarScanner:
    """
    Scans tar headers looking for a target file.
    """
    
    def __init__(self, target_path: str):
        self.target_path = self._normalize_path(target_path)
        self.entries_scanned = 0
        self.current_offset = 0
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path for comparison (remove leading ./ or /)."""
        path = path.strip()
        if path.startswith("./"):
            path = path[2:]
        if path.startswith("/"):
            path = path[1:]
        return path
    
    def _matches(self, entry_name: str) -> bool:
        """Check if entry name matches target."""
        normalized = self._normalize_path(entry_name)
        return normalized == self.target_path
    
    def scan(self, data: bytes) -> ScanResult:
        """
        Scan buffer for target file.
        
        Returns ScanResult indicating whether file was found and where.
        Updates internal state to continue scanning from where we left off.
        """
        while self.current_offset + 512 <= len(data):
            entry, next_offset = parse_tar_header(data, self.current_offset)
            
            if entry is None:
                # End of archive or invalid header
                break
            
            self.entries_scanned += 1
            
            # Check if this is our target
            if self._matches(entry.name):
                content_offset = self.current_offset + 512
                return ScanResult(
                    found=True,
                    entry=entry,
                    content_offset=content_offset,
                    content_size=entry.size,
                    entries_scanned=self.entries_scanned,
                )
            
            # Move to next header
            if next_offset <= self.current_offset:
                break
            self.current_offset = next_offset
        
        return ScanResult(
            found=False,
            entries_scanned=self.entries_scanned,
        )
    
    def needs_more_data(self, buffer_size: int) -> bool:
        """Check if we need more data to continue scanning."""
        return self.current_offset + 512 > buffer_size


# =============================================================================
# File Extraction and Saving
# =============================================================================

def extract_and_save(
    data: bytes,
    content_offset: int,
    content_size: int,
    target_path: str,
    output_dir: str,
) -> str:
    """
    Extract file content from buffer and save to disk.
    
    Returns the path where file was saved.
    """
    # Extract content
    content = data[content_offset:content_offset + content_size]
    
    # Prepare output path - remove leading slash from target path
    clean_path = target_path.lstrip("/")
    output_path = Path(output_dir) / clean_path
    
    # Create parent directories
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write file
    output_path.write_bytes(content)
    
    return str(output_path)


# =============================================================================
# Main Carving Logic
# =============================================================================

def carve_file(
    image_ref: str,
    target_path: str,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    verbose: bool = True,
) -> CarveResult:
    """
    Carve a single file from a Docker image layer.
    
    Uses HTTP Range requests to fetch compressed data incrementally,
    decompresses on-the-fly, and stops as soon as the target file
    is fully extracted.
    
    Args:
        image_ref: Image reference (e.g., "nginx:alpine", "ubuntu:24.04")
        target_path: Target file path in container (e.g., "/etc/passwd")
        output_dir: Output directory for carved file (default: ./carved)
        chunk_size: Fetch chunk size in bytes (default: 64KB)
        verbose: Whether to show detailed progress output
        
    Returns:
        CarveResult with extraction stats and status
    """
    start_time = time.time()
    
    # Parse image reference
    namespace, repo, tag = parse_image_ref(image_ref)
    
    # Step 1: Authenticate using centralized RegistryAuth
    if verbose:
        print(f"Fetching manifest for {namespace}/{repo}:{tag}...")
    
    auth = RegistryAuth(namespace, repo)
    
    try:
        # Step 2: Get manifest and layers
        layers = _fetch_manifest(auth, namespace, repo, tag)
        if not layers:
            return CarveResult(
                found=False,
                target_file=target_path,
                error="No layers found in manifest",
            )
        
        if verbose:
            print(f"Found {len(layers)} layer(s). Searching for {target_path}...\n")
        
        # Step 3: Scan each layer
        for i, layer in enumerate(layers):
            if verbose:
                print(f"Scanning layer {i+1}/{len(layers)}: {layer.digest[:20]}...")
                print(f"  Layer size: {layer.size:,} bytes")
            
            # Initialize components
            reader = IncrementalBlobReader(auth, namespace, repo, layer.digest, chunk_size)
            decompressor = IncrementalGzipDecompressor()
            scanner = TarScanner(target_path)
            
            # Stream and scan
            chunks_fetched = 0
            while not reader.exhausted:
                # Fetch next chunk
                compressed = reader.fetch_chunk()
                if not compressed:
                    break
                
                chunks_fetched += 1
                
                # Check gzip magic on first chunk
                if chunks_fetched == 1:
                    if len(compressed) < 2 or compressed[0:2] != b'\x1f\x8b':
                        if verbose:
                            print(f"  Layer is not gzip compressed, skipping")
                        break
                
                # Decompress
                decompressor.feed(compressed)
                
                if decompressor.error:
                    if verbose:
                        print(f"  Decompression error: {decompressor.error}")
                    break
                
                # Scan for target
                result = scanner.scan(decompressor.get_buffer())
                
                if verbose:
                    print(f"  Downloaded: {reader.bytes_downloaded:,}B -> "
                          f"Decompressed: {decompressor.bytes_decompressed:,}B -> "
                          f"Entries: {scanner.entries_scanned}")
                
                if result.found:
                    # Check if we have enough data for the file content
                    buffer = decompressor.get_buffer()
                    bytes_needed = result.content_offset + result.content_size
                    
                    # Fetch more if needed
                    while len(buffer) < bytes_needed and not reader.exhausted:
                        compressed = reader.fetch_chunk()
                        if not compressed:
                            break
                        decompressor.feed(compressed)
                        buffer = decompressor.get_buffer()
                        if verbose:
                            print(f"  Fetching more for file content... "
                                  f"Have {len(buffer):,} / need {bytes_needed:,}")
                    
                    buffer = decompressor.get_buffer()
                    if len(buffer) >= bytes_needed:
                        # Found and have full content!
                        if verbose:
                            print(f"  FOUND: {target_path} ({result.content_size:,} bytes) "
                                  f"at entry #{result.entries_scanned}")
                        
                        # Extract and save
                        saved_path = extract_and_save(
                            buffer,
                            result.content_offset,
                            result.content_size,
                            target_path,
                            output_dir,
                        )
                        
                        elapsed = time.time() - start_time
                        efficiency = (reader.bytes_downloaded / layer.size * 100) if layer.size else 0
                        
                        if verbose:
                            print(f"\nDone! File saved to: {saved_path}")
                            print(f"Stats: Downloaded {reader.bytes_downloaded:,} bytes "
                                  f"of {layer.size:,} byte layer ({efficiency:.1f}%) "
                                  f"in {elapsed:.2f}s")
                        
                        return CarveResult(
                            found=True,
                            saved_path=saved_path,
                            target_file=target_path,
                            bytes_downloaded=reader.bytes_downloaded,
                            layer_size=layer.size,
                            efficiency_pct=efficiency,
                            elapsed_time=elapsed,
                            layer_digest=layer.digest,
                            layers_searched=i + 1,
                        )
                    else:
                        if verbose:
                            print(f"  [!] Found file but couldn't get full content")
                            print(f"      Have {len(buffer):,} bytes, need {bytes_needed:,}")
            
            if verbose:
                print()  # Blank line between layers
        
        elapsed = time.time() - start_time
        if verbose:
            print(f"File not found: {target_path} (searched {len(layers)} layers in {elapsed:.2f}s)")
        
        return CarveResult(
            found=False,
            target_file=target_path,
            elapsed_time=elapsed,
            layers_searched=len(layers),
        )
    
    finally:
        # Always invalidate auth session when done
        auth.invalidate()


# =============================================================================
# CLI Entry Point (standalone usage)
# =============================================================================

def main():
    """Standalone CLI for file carving."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Extract a single file from a Docker image layer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python carver.py ubuntu:24.04 /etc/passwd
  python carver.py nginx:alpine /etc/nginx/nginx.conf
  python carver.py alpine:edge /etc/os-release
  python carver.py aciliadevops/disney-local-web:latest /etc/passwd
  python carver.py alpine /etc/os-release  # defaults to :latest
        """
    )
    
    parser.add_argument(
        "image",
        help="Docker image reference (e.g., 'ubuntu:24.04', 'nginx:alpine', 'user/repo:tag')"
    )
    parser.add_argument(
        "filepath",
        help="Target file path in container (e.g., '/etc/passwd')"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--chunk-size", "-c",
        type=int,
        default=DEFAULT_CHUNK_SIZE // 1024,
        help=f"Fetch chunk size in KB (default: {DEFAULT_CHUNK_SIZE // 1024})"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress detailed progress output"
    )
    
    args = parser.parse_args()
    
    # Run carve
    result = carve_file(
        image_ref=args.image,
        target_path=args.filepath,
        output_dir=args.output_dir,
        chunk_size=args.chunk_size * 1024,
        verbose=not args.quiet,
    )
    
    import sys
    sys.exit(0 if result.found else 1)


if __name__ == "__main__":
    main()
