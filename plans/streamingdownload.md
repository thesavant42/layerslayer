Yes, you can serve the layer blob directly as a browser download using FastAPI's `StreamingResponse`. The key is to:

1. Set `Content-Type` to `application/gzip` (or `application/octet-stream`)
2. Set `Content-Disposition` header with `attachment; filename="..."` to trigger the browser's download dialog
3. Stream the upstream response directly to the client (no filesystem involved)

Here's how the approach would work in your [`api.py`](app/modules/api/api.py):

```python
from fastapi.responses import StreamingResponse

@app.get("/layer/download")
def download_layer(
    image: str,
    digest: str,
    arch: int = Query(default=0)
):
    """
    Stream a layer blob directly to the browser as a download.
    """
    from app.modules.auth import RegistryAuth
    from app.modules.formatters.formatters import parse_image_ref, registry_base_url
    
    user, repo, _ = parse_image_ref(image)
    url = f"{registry_base_url(user, repo)}/blobs/{digest}"
    
    auth = RegistryAuth()
    resp = auth.request_with_retry("GET", url, stream=True)
    resp.raise_for_status()
    
    # Generate a clean filename from the digest
    filename = digest.replace(":", "_") + ".tar.gz"
    
    # Stream the response content directly to the browser
    return StreamingResponse(
        resp.iter_content(chunk_size=8192),
        media_type="application/gzip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": resp.headers.get("Content-Length", ""),
        }
    )
```

The flow:

```
Browser ──GET /layer/download──> FastAPI ──authenticated GET──> Registry
                                    │
Registry ──chunked response──> FastAPI ──StreamingResponse──> Browser
                                                                  │
                                                           Save dialog appears
```

**Key headers:**

| Header | Purpose |
|--------|---------|
| `Content-Type: application/gzip` | Tells browser it's a gzip file |
| `Content-Disposition: attachment; filename="..."` | Triggers download dialog with suggested filename |
| `Content-Length` | Optional but helps browser show download progress |

**Why this is efficient:**
- No disk I/O - data streams from registry through your API directly to the browser
- Memory efficient - only 8KB chunks held in memory at a time via `iter_content()`
- Backpressure handled - FastAPI/Starlette automatically handles slow clients

This pattern is commonly called a "proxy download" or "passthrough streaming" - your API acts as an authenticated proxy that adds the credentials the browser doesn't have, then forwards the response directly.