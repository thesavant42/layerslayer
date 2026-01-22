# Plan: Add Plain Text Viewing to /carve Endpoint

## Overview

Add an `as_text` query parameter to the `/carve` endpoint that returns carved file contents as plain text rendered inline in the browser, rather than triggering a file download.

## Current State

**File:** `app/modules/api/api.py`  
**Endpoint:** `/carve` (lines 357-410)

Current signature:
```python
@app.get("/carve")
def carve(
    image: str,
    path: str = Query(..., description="File path in container, e.g., /etc/passwd"),
):
```

Current response (always triggers download):
```python
return Response(
    content=content,
    media_type=media_type,
    headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Length": str(len(content)),
        "X-Carve-Efficiency": f"{result.efficiency_pct:.1f}%",
        "X-Carve-Bytes-Downloaded": str(result.bytes_downloaded),
        "X-Carve-Layer-Size": str(result.layer_size),
        "X-Carve-Layer-Digest": result.layer_digest or "",
        "X-Carve-Elapsed-Time": f"{result.elapsed_time:.2f}s",
    }
)
```

---

## Proposed Changes

### Change 1: Add Query Parameter

**Location:** Line 358-361

**Before:**
```python
def carve(
    image: str,
    path: str = Query(..., description="File path in container, e.g., /etc/passwd"),
):
```

**After:**
```python
def carve(
    image: str,
    path: str = Query(..., description="File path in container, e.g., /etc/passwd"),
    as_text: bool = Query(default=False, description="Render as plain text in browser instead of downloading"),
):
```

---

### Change 2: Conditional Response Headers

**Location:** Lines 398-410 (the return statement)

**Before:**
```python
return Response(
    content=content,
    media_type=media_type,
    headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Length": str(len(content)),
        "X-Carve-Efficiency": f"{result.efficiency_pct:.1f}%",
        "X-Carve-Bytes-Downloaded": str(result.bytes_downloaded),
        "X-Carve-Layer-Size": str(result.layer_size),
        "X-Carve-Layer-Digest": result.layer_digest or "",
        "X-Carve-Elapsed-Time": f"{result.elapsed_time:.2f}s",
    }
)
```

**After:**
```python
# Build common headers
headers = {
    "Content-Length": str(len(content)),
    "X-Carve-Efficiency": f"{result.efficiency_pct:.1f}%",
    "X-Carve-Bytes-Downloaded": str(result.bytes_downloaded),
    "X-Carve-Layer-Size": str(result.layer_size),
    "X-Carve-Layer-Digest": result.layer_digest or "",
    "X-Carve-Elapsed-Time": f"{result.elapsed_time:.2f}s",
}

if as_text:
    # Inline display as plain text
    headers["Content-Disposition"] = f'inline; filename="{filename}"'
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers=headers,
    )
else:
    # Download as file (existing behavior)
    headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return Response(
        content=content,
        media_type=media_type,
        headers=headers,
    )
```

---

## Usage Examples

| Request | Behavior |
|---------|----------|
| `/carve?image=nginx/nginx:alpine&path=/etc/passwd` | Downloads `passwd` file |
| `/carve?image=nginx/nginx:alpine&path=/etc/passwd&as_text=true` | Renders contents in browser |
| `/carve?image=nginx/nginx:alpine&path=/app/config.json&as_text=true` | Renders JSON as plain text |

---

## Files Modified

| File | Change |
|------|--------|
| `app/modules/api/api.py` | Add `as_text` parameter and conditional response logic |

---

## Testing

1. **Download mode (default):** Verify `/carve?image=nginx/nginx:alpine&path=/etc/os-release` triggers file download
2. **Text mode:** Verify `/carve?image=nginx/nginx:alpine&path=/etc/os-release&as_text=true` renders text inline
3. **Headers:** Confirm `X-Carve-*` headers are present in both modes

---

## Notes

- Binary files requested with `as_text=true` will display as garbled text - this is expected user behavior
- No changes required to `carver.py` - only the API response handling changes
