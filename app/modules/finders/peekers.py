import os
import io, tarfile, zlib, requests
from typing import Optional, List, Generator

from app.modules.formatters import parse_image_ref, registry_base_url, human_readable_size
from app.modules.finders.tar_parser import TarEntry, parse_tar_header

from app.modules.auth.auth import fetch_pull_token
from app.modules.finders.layerPeekResult import LayerPeekResult
from app.modules.formatters.formatters import _tarinfo_mode_to_string, _format_mtime

# =============================================================================
# Layer Peek - Streaming with complete enumeration
# =============================================================================
# in what ways is this different than peek_layer_blob_streaming?
def peek_layer_blob(image_ref, digest, token=None):
    """
    Download a layer blob and list ALL its contents using streaming decompression.
    This enumerates EVERY file in the layer.
    """
    user, repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url(user, repo)}/blobs/{digest}"

    # Build headers
    headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        # Try to get a fresh token
        token = fetch_pull_token(user, repo)
        if token:
            headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(url, headers=headers, stream=True, timeout=60)
    if resp.status_code == 401:
        print(" Unauthorized. Fetching fresh pull token...")
        new_token = fetch_pull_token(user, repo)
        if new_token:
            headers["Authorization"] = f"Bearer {new_token}"
            resp = requests.get(url, headers=headers, stream=True, timeout=60)

    resp.raise_for_status()

    # Use tarfile for complete enumeration with streaming
    tar_bytes = io.BytesIO(resp.content)
    with tarfile.open(fileobj=tar_bytes, mode="r:gz") as tar:
        print("\n Layer contents:\n")
        for member in tar.getmembers():
            if member.isdir():
                print(f"  [DIR] {member.name}/")
            else:
                size = human_readable_size(member.size)
                print(f"  [FILE] {member.name} ({size})")


def peek_layer_blob_complete(
    image_ref: str,
    digest: str,
    layer_size: int = 0,
    token: Optional[str] = None,
) -> LayerPeekResult:
    """
    Stream and decompress the ENTIRE layer to enumerate ALL files.
    
    Uses streaming decompression to minimize memory usage while
    enumerating every file in the tar archive. This is used to populate the 
    vtty datatable, DO NOT TOUCH
    
    Args:
        image_ref: Image reference (e.g., "nginx:latest")
        digest: Layer digest (e.g., "sha256:abc123...")
        layer_size: Total layer size (for progress display)
        token: Optional auth token
        
    Returns:
        LayerPeekResult with COMPLETE *file listing*
    """
    user, repo, _ = parse_image_ref(image_ref)
    
    # Get token if not provided
    if not token:
        token = fetch_pull_token(user, repo)
    
    url = f"{registry_base_url(user, repo)}/blobs/{digest}"
    
    # Build headers
    headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        resp = requests.get(url, headers=headers, stream=True, timeout=120)
        
        # Handle auth retry
        if resp.status_code == 401:
            token = fetch_pull_token(user, repo)
            if token:
                headers["Authorization"] = f"Bearer {token}"
                resp = requests.get(url, headers=headers, stream=True, timeout=120)
        
        resp.raise_for_status()
        
    except requests.RequestException as e:
        return LayerPeekResult(
            digest=digest,
            partial=False,
            bytes_downloaded=0,
            bytes_decompressed=0,
            entries_found=0,
            entries=[],
            error=str(e),
        )
    
    # Stream into BytesIO for tarfile processing
    compressed_data = resp.content
    bytes_downloaded = len(compressed_data)
    
    try:
        tar_bytes = io.BytesIO(compressed_data)
        entries: List[TarEntry] = []
        bytes_decompressed = 0
        
        with tarfile.open(fileobj=tar_bytes, mode="r:gz") as tar:
            for member in tar.getmembers():
                # Convert tarfile.TarInfo to our TarEntry format
                typeflag = '5' if member.isdir() else ('2' if member.issym() else '0')
                mode_str = _tarinfo_mode_to_string(member.mode, typeflag)
                
                entry = TarEntry(
                    name=member.name,
                    size=member.size,
                    typeflag=typeflag,
                    is_dir=member.isdir(),
                    mode=mode_str,
                    uid=member.uid,
                    gid=member.gid,
                    mtime=_format_mtime(member.mtime),
                    linkname=member.linkname if member.issym() else "",
                    is_symlink=member.issym(),
                )
                entries.append(entry)
                bytes_decompressed += 512 + member.size  # header + content
        
        return LayerPeekResult(
            digest=digest,
            partial=False,  # COMPLETE enumeration
            bytes_downloaded=bytes_downloaded,
            bytes_decompressed=bytes_decompressed,
            entries_found=len(entries),
            entries=entries,
        )
        
    except Exception as e:
        return LayerPeekResult(
            digest=digest,
            partial=False,
            bytes_downloaded=bytes_downloaded,
            bytes_decompressed=0,
            entries_found=0,
            entries=[],
            error=f"Tar extraction error: {e}",
        )

# LOOK HERE TODO WE  DONT WANT THIS
def peek_layer_blob_partial(
    image_ref: str,
    digest: str,
    token: Optional[str] = None,
    initial_bytes: int = 262144,
) -> LayerPeekResult:
    """
    Fetch only first N bytes of a layer using HTTP Range request,
    decompress, and parse tar headers.
    
    Returns PARTIAL file listing for quick preview.
    For complete listing, use peek_layer_blob_complete().
    
    Args:
        image_ref: Image reference (e.g., "nginx:latest")
        digest: Layer digest (e.g., "sha256:abc123...")
        token: Optional auth token
        initial_bytes: How many bytes to fetch (default 256KB)
        
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
# END OF LOOK HERE

# KEEP ME
def peek_layer_blob_streaming(
    image_ref: str,
    digest: str,
    token: Optional[str] = None,
    initial_bytes: int = 262144,
) -> Generator[TarEntry, None, LayerPeekResult]:
    """
    Generator version that yields entries as they are parsed.
    
    This allows the UI to display entries progressively as they're discovered.
    
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

