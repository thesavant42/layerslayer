import io
import tarfile
import zlib
import requests
from typing import Optional, List, Generator

from app.modules.formatters import parse_image_ref, registry_base_url, human_readable_size
from app.modules.finders.tar_parser import TarEntry, parse_tar_header
from app.modules.auth import RegistryAuth
from app.modules.finders.layerPeekResult import LayerPeekResult
from app.modules.formatters.formatters import _tarinfo_mode_to_string, _format_mtime


# =============================================================================
# Incremental Streaming Components
# =============================================================================

class IncrementalGzipDecompressor:
    """
    Decompresses gzip data incrementally, maintaining state across chunk feeds.
    
    Usage:
        decompressor = IncrementalGzipDecompressor()
        while has_more_data:
            decompressor.feed(compressed_chunk)
            buffer = decompressor.get_buffer()
            # parse buffer...
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


class IncrementalBlobReader:
    """
    Fetches blob data in chunks using HTTP Range requests.
    
    Usage:
        reader = IncrementalBlobReader(auth, namespace, repo, digest)
        while not reader.exhausted:
            chunk = reader.fetch_chunk()
            # process chunk...
    """
    
    def __init__(
        self,
        auth: RegistryAuth,
        namespace: str,
        repo: str,
        digest: str,
        chunk_size: int = 65536,  # 64KB default
    ):
        self.auth = auth
        self.url = f"{registry_base_url(namespace, repo)}/blobs/{digest}"
        self.chunk_size = chunk_size
        self.current_offset = 0
        self.bytes_downloaded = 0
        self.total_size = 0  # Set after first request from Content-Range
        self.exhausted = False
    
    def fetch_chunk(self) -> bytes:
        """
        Fetch the next chunk of data using HTTP Range request.
        Returns empty bytes if exhausted or on error.
        """
        if self.exhausted:
            return b""
        
        end_offset = self.current_offset + self.chunk_size - 1
        
        # Get session and add Range header
        session = self.auth.get_session()
        headers = {"Range": f"bytes={self.current_offset}-{end_offset}"}
        
        try:
            resp = session.get(self.url, headers=headers, stream=True, timeout=30)
            
            # 416 means range not satisfiable (past end of file)
            if resp.status_code == 416:
                self.exhausted = True
                return b""
            
            # Handle 401 by refreshing token and retrying
            if resp.status_code == 401:
                self.auth._token = None
                session = self.auth.get_session()
                resp = session.get(self.url, headers=headers, stream=True, timeout=30)
            
            resp.raise_for_status()
            
            # Get total size from Content-Range header (format: "bytes 0-65535/12345678")
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
            
        except requests.RequestException:
            self.exhausted = True
            return b""


# =============================================================================
# Layer Peek - Incremental Streaming
# =============================================================================

def peek_layer_streaming(
    auth: RegistryAuth,
    image_ref: str,
    digest: str,
    layer_size: int = 0,
    chunk_size: int = 65536,
) -> LayerPeekResult:
    """
    Stream and parse layer tar headers incrementally using HTTP Range requests.
    
    Uses chunked fetching via IncrementalBlobReader to avoid loading the
    entire compressed layer into memory. Parses tar headers as data becomes
    available using parse_tar_header().
    
    This is the primary function for enumerating layer contents.
    
    Args:
        auth: RegistryAuth instance for authenticated requests
        image_ref: Image reference (e.g., "nginx:latest")
        digest: Layer digest (e.g., "sha256:abc123...")
        layer_size: Total layer size (for info only, not used in logic)
        chunk_size: Bytes to fetch per HTTP Range request (default 64KB)
        
    Returns:
        LayerPeekResult with complete file listing
    """
    user, repo, _ = parse_image_ref(image_ref)
    
    reader = IncrementalBlobReader(auth, user, repo, digest, chunk_size)
    decompressor = IncrementalGzipDecompressor()
    entries: List[TarEntry] = []
    parse_offset = 0
    first_chunk = True
    
    while not reader.exhausted:
        compressed = reader.fetch_chunk()
        if not compressed:
            break
        
        # First chunk: verify gzip magic bytes (0x1f 0x8b)
        if first_chunk:
            first_chunk = False
            if len(compressed) < 2 or compressed[0:2] != b'\x1f\x8b':
                return LayerPeekResult(
                    digest=digest,
                    partial=False,
                    bytes_downloaded=reader.bytes_downloaded,
                    bytes_decompressed=0,
                    entries_found=0,
                    entries=[],
                    error="Not a gzip file (missing magic bytes)",
                )
        
        decompressor.feed(compressed)
        
        if decompressor.error:
            return LayerPeekResult(
                digest=digest,
                partial=False,
                bytes_downloaded=reader.bytes_downloaded,
                bytes_decompressed=decompressor.bytes_decompressed,
                entries_found=len(entries),
                entries=entries,
                error=f"Decompression error: {decompressor.error}",
            )
        
        buffer = decompressor.get_buffer()
        
        # Parse all available tar headers from current buffer
        while parse_offset + 512 <= len(buffer):
            entry, next_offset = parse_tar_header(buffer, parse_offset)
            if entry is None:
                # End of archive or need more data
                break
            entries.append(entry)
            if next_offset <= parse_offset:
                break
            parse_offset = next_offset
    
    return LayerPeekResult(
        digest=digest,
        partial=False,
        bytes_downloaded=reader.bytes_downloaded,
        bytes_decompressed=decompressor.bytes_decompressed,
        entries_found=len(entries),
        entries=entries,
    )


# KEEP ME
def peek_layer_blob_streaming(
    auth: RegistryAuth,
    image_ref: str,
    digest: str,
    initial_bytes: int = 262144,
) -> Generator[TarEntry, None, LayerPeekResult]:
    """
    Generator version that yields entries as they are parsed.
    
    This allows the UI to display entries progressively as they're discovered.
    
    Args:
        auth: RegistryAuth instance for authenticated requests
        image_ref: Image reference (e.g., "nginx:latest")
        digest: Layer digest (e.g., "sha256:abc123...")
        initial_bytes: How many bytes to fetch (default 256KB)
    
    Yields:
        TarEntry objects as they are parsed
        
    Returns:
        LayerPeekResult with final stats (accessible via generator.value)
    """
    user, repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url(user, repo)}/blobs/{digest}"
    
    # Get session and add Range header
    session = auth.get_session()
    headers = {"Range": f"bytes=0-{initial_bytes - 1}"}
    
    error_msg = None
    compressed_data = b""
    decompressed = b""
    entries = []
    
    try:
        resp = session.get(url, headers=headers, stream=True, timeout=30)
        
        # Handle auth retry
        if resp.status_code == 401:
            auth._token = None
            session = auth.get_session()
            resp = session.get(url, headers=headers, stream=True, timeout=30)
        
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
