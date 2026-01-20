# Fix Plan: Layer Peeking Streaming Bug

## Problem Summary

The current [`peek_layer_streaming()`](../../app/modules/finders/peekers.py:146) function downloads entire layers instead of peeking at just the headers. This defeats the purpose of the "tar.gz hack" optimization.

**Root Cause**: The outer while loop has no byte limit - it continues until `archive_complete` (null block found) or `reader.exhausted` (all data downloaded).

---

## Current Broken Code

```python
# peekers.py lines 181-229
while not reader.exhausted and not archive_complete:
    compressed = reader.fetch_chunk()
    if not compressed:
        break
    
    # ... decompression and parsing ...
    
    while parse_offset + 512 <= len(buffer):
        if buffer[parse_offset:parse_offset + 512] == b'\x00' * 512:
            archive_complete = True  # Only way to exit cleanly
            break
        # ... parse headers ...
```

**Problem**: No `max_bytes` check in the outer loop. Downloads entire layer.

---

## Fix Strategy

Add a `max_bytes` parameter to `peek_layer_streaming()` with a **default of 256KB** that terminates fetching early. This implements the "tar.gz hack" - fetching only enough compressed data to enumerate file headers without downloading entire layers.

The 256KB byte limit is the standard behavior. No CLI flags needed.

---

## Detailed Implementation Plan

### Step 1: Modify `peek_layer_streaming()` Signature

**File**: `app/modules/finders/peekers.py`

**Current**:
```python
def peek_layer_streaming(
    auth: RegistryAuth,
    image_ref: str,
    digest: str,
    layer_size: int = 0,
    chunk_size: int = 65536,
) -> LayerPeekResult:
```

**Fixed**:
```python
def peek_layer_streaming(
    auth: RegistryAuth,
    image_ref: str,
    digest: str,
    layer_size: int = 0,
    chunk_size: int = 65536,
    max_bytes: int = 262144,  # 256KB default - the tar.gz hack
) -> LayerPeekResult:
```

---

### Step 2: Add Early Termination to Main Loop

**File**: `app/modules/finders/peekers.py`

**Current**:
```python
while not reader.exhausted and not archive_complete:
    compressed = reader.fetch_chunk()
    if not compressed:
        break
```

**Fixed**:
```python
while not reader.exhausted and not archive_complete:
    # Early termination based on byte budget (the "tar.gz hack")
    if reader.bytes_downloaded >= max_bytes:
        break
    
    compressed = reader.fetch_chunk()
    if not compressed:
        break
```

---

### Step 3: Keep Return Value Simple

The `partial` field in `LayerPeekResult` should always be `False` since there's no distinction between "partial" and "complete" peeking. Each layer is peeked fully within the byte budget.

```python
return LayerPeekResult(
    digest=digest,
    partial=False,
    bytes_downloaded=reader.bytes_downloaded,
    bytes_decompressed=decompressor.bytes_decompressed,
    entries_found=len(entries),
    entries=entries,
)
```

---

### Step 4: Update `layerslayer()` in layerSlayerResults.py

Add `max_bytes` parameter to pass through to `peek_layer_streaming()`:

**Current**:
```python
def layerslayer(
    image_ref: str,
    layers: list[dict],
    auth: Optional[RegistryAuth] = None,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> LayerSlayerResult:
```

**Fixed**:
```python
def layerslayer(
    image_ref: str,
    layers: list[dict],
    auth: Optional[RegistryAuth] = None,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
    max_bytes: int = 262144,  # 256KB default
) -> LayerSlayerResult:
```

And update the call:
```python
result = peek_layer_streaming(
    auth=auth,
    image_ref=image_ref,
    digest=digest,
    layer_size=layer_size,
    max_bytes=max_bytes,
)
```

---

### Step 5: No CLI Changes Needed

The 256KB byte limit is the standard behavior. Callers use defaults.

---

## Complete Modified `peek_layer_streaming()` Function

```python
def peek_layer_streaming(
    auth: RegistryAuth,
    image_ref: str,
    digest: str,
    layer_size: int = 0,
    chunk_size: int = 65536,
    max_bytes: int = 262144,  # 256KB default - the tar.gz hack
) -> LayerPeekResult:
    """
    Stream and parse layer tar headers incrementally using HTTP Range requests.
    
    Uses chunked fetching via IncrementalBlobReader to minimize bandwidth.
    Implements the "tar.gz hack" - fetching only enough compressed data to
    enumerate file headers without downloading entire layers.
    
    This is the primary function for enumerating layer contents.
    
    Args:
        auth: RegistryAuth instance for authenticated requests
        image_ref: Image reference (e.g., "nginx:latest")
        digest: Layer digest (e.g., "sha256:abc123...")
        layer_size: Total layer size (for info only, not used in logic)
        chunk_size: Bytes to fetch per HTTP Range request (default 64KB)
        max_bytes: Maximum compressed bytes to download (default 256KB)
        
    Returns:
        LayerPeekResult with file listing
    """
    user, repo, _ = parse_image_ref(image_ref)
    
    reader = IncrementalBlobReader(auth, user, repo, digest, chunk_size)
    decompressor = IncrementalGzipDecompressor()
    entries: List[TarEntry] = []
    parse_offset = 0
    first_chunk = True
    archive_complete = False
    
    while not reader.exhausted and not archive_complete:
        # Early termination based on byte budget (the "tar.gz hack")
        if reader.bytes_downloaded >= max_bytes:
            break
        
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
            # Check for null block BEFORE calling parse_tar_header
            if buffer[parse_offset:parse_offset + 512] == b'\x00' * 512:
                archive_complete = True
                break
            
            entry, next_offset = parse_tar_header(buffer, parse_offset)
            if entry is None:
                # Not enough data or parse error - need more chunks
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
```

---

## Files to Modify

1. **`app/modules/finders/peekers.py`**
   - Add `max_bytes` parameter with default 262144 (256KB)
   - Add early termination check in main loop
   - Always set `partial=False` in return

2. **`app/modules/keepers/layerSlayerResults.py`**
   - Add `max_bytes` parameter to `layerslayer()`
   - Pass through to `peek_layer_streaming()`

3. **`main.py`** - No changes needed (uses defaults)

---

## Testing Plan

### Test 1: Verify Byte Limit Works
```bash
# Should download ~256KB per layer (not the full layer size)
python main.py -t nginx:alpine --peek-all
```

### Test 2: Verify Efficiency
```bash
# Compare bytes_downloaded vs layer_size in output
# Should be ~0.5-5% of layer size depending on compression
```

### Test 3: Verify Headers Found
```bash
# Should find multiple file entries from the 256KB of data
# Check that entries are being enumerated correctly
```

---

## Success Criteria

1. Downloads ~256KB per layer regardless of layer size
2. Returns within seconds for any layer
3. Enumerates file headers from the downloaded data
4. No changes to CLI interface needed

---


## Summary: Core Differences in Tar Parsing Techniques

### Working Old Version (Commit 9098b5be)
The old version used a **byte-limited single HTTP Range request**:
1. Fetched a fixed amount of compressed data (~256KB) via HTTP Range header
2. Decompressed what was fetched
3. Parsed tar headers from the decompressed buffer using [`parse_tar_header()`](app/modules/finders/tar_parser.py)
4. **Stopped after hitting byte limit** - connection severed immediately

Key code pattern:
```python
headers = {"Range": f"bytes=0-{initial_bytes - 1}"}
resp = session.get(url, headers=headers)
compressed_data = resp.raw.read(initial_bytes)
resp.close()  # Sever connection immediately
```

### Current Broken Version
The current version has **no byte limit in the outer loop**:
1. Fetches chunks in a loop until either:
   - `archive_complete` (null block found - end of tar archive)
   - `reader.exhausted` (entire blob downloaded)
2. Downloads entire layers because null block only appears at archive end

Key issue in [`peek_layer_streaming()`](app/modules/finders/peekers.py:146):
```python
while not reader.exhausted and not archive_complete:
    compressed = reader.fetch_chunk()  # No byte limit check!
```

### The Fix Applied
Added `max_bytes=262144` (256KB) default and early termination:
```python
while not reader.exhausted and not archive_complete:
    if reader.bytes_downloaded >= max_bytes:  # THE FIX
        break
    compressed = reader.fetch_chunk()
```

This restores the "tar.gz hack" - fetching only enough compressed data to enumerate file headers without downloading entire layers.