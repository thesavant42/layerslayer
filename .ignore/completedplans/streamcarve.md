File Carving is not yet fully exposed to the API
**COMPLETED**
**Status of carver.py coupling:**

Based on the codebase search, [`carver.py`](app/modules/keepers/carver.py) is currently:
- Used by [`main.py`](main.py:17) for CLI carve mode (`--carve-file`)
- Imported by [`layerslayer.py`](app/modules/keepers/layerslayer.py:18)
- **NOT exposed via the API** - there's no `/carve` endpoint in [`api.py`](app/modules/api/api.py)

The carver still saves to filesystem via [`extract_and_save()`](app/modules/keepers/carver.py:332-357). However, the good news is that **the data is already fully in memory** before the disk write happens - see line 472-486 in [`carve_file()`](app/modules/keepers/carver.py:472-486):

```python
buffer = decompressor.get_buffer()
if len(buffer) >= bytes_needed:
    # Found and have full content!
    saved_path = extract_and_save(  # <-- This is where disk I/O happens
        buffer,
        result.content_offset,
        result.content_size,
        ...
    )
```

**Can carver stream to browser? Yes, with a small refactor.**

The pattern differs from layer download because carver doesn't stream from upstream - it incrementally fetches, decompresses, and scans until it finds the file. By that point, the file content is already fully loaded in `buffer[content_offset:content_offset + content_size]`.

Here's how to adapt it:

```python
from fastapi import Response

def carve_file_to_bytes(
    image_ref: str,
    target_path: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> tuple[bytes, CarveResult]:
    """
    Carve a file but return bytes instead of saving to disk.
    Returns (file_content, result) tuple.
    """
    # ... same logic as carve_file() until line 472 ...
    
    buffer = decompressor.get_buffer()
    if len(buffer) >= bytes_needed:
        # Extract content to bytes instead of saving
        content = buffer[result.content_offset:result.content_offset + result.content_size]
        
        return content, CarveResult(
            found=True,
            target_file=target_path,
            # ... stats ...
        )


@app.get("/carve")
def carve_endpoint(
    image: str,
    path: str,  # e.g., /etc/passwd
):
    """
    Carve a single file from a Docker image and return it as a download.
    """
    content, result = carve_file_to_bytes(image, path)
    
    if not result.found:
        raise HTTPException(404, f"File not found: {path}")
    
    filename = Path(path).name  # e.g., "passwd" from "/etc/passwd"
    
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Carve-Efficiency": f"{result.efficiency_pct:.1f}%",
            "X-Carve-Bytes-Downloaded": str(result.bytes_downloaded),
            "X-Carve-Layer-Size": str(result.layer_size),
        }
    )
```

**Key differences from layer streaming:**

| Aspect | Layer Download | File Carve |
|--------|---------------|------------|
| **Data source** | Stream directly from registry | Incrementally fetch + decompress + scan |
| **Memory model** | Chunks pass through, never fully buffered | File fully buffered before return |
| **Response type** | `StreamingResponse` (chunked) | `Response` (single body) |
| **When to use** | Large blobs (entire layers) | Small files (configs, scripts) |

**Architecture:**

```
Browser ──GET /carve?image=nginx:alpine&path=/etc/passwd──> FastAPI
                                                              │
                                                    carve_file_to_bytes()
                                                              │
                                  ┌───────────── Range Request Loop ─────────────┐
                                  │  1. Fetch 64KB compressed chunk              │
                                  │  2. Decompress incrementally                 │
                                  │  3. Scan tar headers for target              │
                                  │  4. If found, stop; else fetch more          │
                                  └──────────────────────────────────────────────┘
                                                              │
                                                    Return bytes directly
                                                              │
FastAPI ──Response(content=bytes, Content-Disposition: attachment)──> Browser
```

The refactor is minimal - you'd create a `carve_file_to_bytes()` variant that returns the extracted bytes instead of calling [`extract_and_save()`](app/modules/keepers/carver.py:332). The existing carver logic handles all the hard work (auth, manifest parsing, range requests, decompression, tar scanning).