# Docker Hub Search Module - Implementation Plan

## Overview

This plan details how to wire up the existing `search-dockerhub.py` script as an API endpoint at `/search.data` with processed JSON output.

## Architecture

```mermaid
flowchart LR
    A[Client Request] --> B[/search.data API Route]
    B --> C[search module functions]
    C --> D[Docker Hub API]
    D --> C
    C --> E[Parse Response]
    E --> F[Return Processed JSON]
```

## Task Checklist

- [ ] Refactor `search-dockerhub.py` to expose reusable functions
- [ ] Wire up `app/modules/search/__init__.py` with exports  
- [ ] Add `/search.data` route to `app/modules/api/api.py`
- [ ] Test the endpoint

---

## Step 1: Refactor search-dockerhub.py

The existing script has the core logic but only works as CLI. We need to extract the search functionality into a callable async function.

### Current State

The script has these useful functions:
- `resolve(data, idx)` - Parses Docker Hub's flat array format
- `get_results(data)` - Extracts results and total count
- `format_date(iso_str)` - Date formatting helper

### Changes Needed

Add a new async function `search_dockerhub()` that:
1. Accepts query parameters
2. Makes the HTTP request using `httpx` (async)
3. Parses the response
4. Returns structured JSON

### Code Example

Add this function to [`search-dockerhub.py`](../../app/modules/search/search-dockerhub.py):

```python
import httpx

async def search_dockerhub(
    query: str,
    page: int = 1,
    sortby: str = None,
    order: str = "desc"
) -> dict:
    """
    Search Docker Hub and return processed results.
    
    Args:
        query: Search term
        page: Page number (default 1)
        sortby: Sort field - 'pull_count' or 'updated_at'
        order: Sort order - 'asc' or 'desc' (default 'desc')
    
    Returns:
        dict with 'results' list and 'total' count
    """
    url = "https://hub.docker.com/search.data"
    params = {
        'q': query,
        'page': page,
        'order': order
    }
    if sortby:
        params['sortby'] = sortby
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    
    results, total = get_results(data)
    
    # Format the results for API response
    formatted_results = []
    for r in results:
        formatted_results.append({
            'slug': r.get('id', ''),
            'star_count': r.get('star_count', 0),
            'pull_count': r.get('pull_count', '0'),
            'publisher': r.get('publisher', {}),
            'created_at': r.get('created_at', ''),
            'updated_at': r.get('updated_at', ''),
            'short_description': r.get('short_description', '')
        })
    
    return {
        'total': total,
        'page': page,
        'results': formatted_results
    }
```

---

## Step 2: Wire up __init__.py

The [`app/modules/search/__init__.py`](../../app/modules/search/__init__.py) file should export the search function for clean imports.

### Code Example

```python
"""Docker Hub Search Module"""

from .search_dockerhub import search_dockerhub, get_results, resolve

__all__ = ['search_dockerhub', 'get_results', 'resolve']
```

**Note:** The hyphen in `search-dockerhub.py` is problematic for Python imports. We should either:
- **Option A:** Rename the file to `search_dockerhub.py` (recommended)
- **Option B:** Use `importlib` like the existing `fs-log-sqlite.py` pattern

### Recommended: Rename file

```
app/modules/search/search-dockerhub.py -> app/modules/search/search_dockerhub.py
```

---

## Step 3: Add API Route

Add the `/search.data` endpoint to [`app/modules/api/api.py`](../../app/modules/api/api.py).

### Import

Add near the top of the file with other imports:

```python
from app.modules.search import search_dockerhub
```

### Route Implementation

Add this route after the existing `/repositories` endpoint:

```python
@app.get("/search.data")
async def search_data(
    q: str = Query(..., description="Search query"),
    page: int = Query(default=1, ge=1, description="Page number"),
    sortby: str = Query(default=None, description="Sort field: pull_count or updated_at"),
    order: str = Query(default="desc", description="Sort order: asc or desc")
):
    """
    Search Docker Hub for images, users, and organizations.
    Returns processed JSON with search results.
    
    Example: /search.data?q=nginx&page=1&sortby=pull_count&order=desc
    """
    # Validate sortby if provided
    if sortby and sortby not in ['pull_count', 'updated_at']:
        raise HTTPException(
            status_code=400, 
            detail="sortby must be 'pull_count' or 'updated_at'"
        )
    
    # Validate order
    if order not in ['asc', 'desc']:
        raise HTTPException(
            status_code=400,
            detail="order must be 'asc' or 'desc'"
        )
    
    try:
        result = await search_dockerhub(
            query=q,
            page=page,
            sortby=sortby,
            order=order
        )
        return JSONResponse(content=result, status_code=200)
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Docker Hub API error: {e.response.text}"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to connect to Docker Hub: {str(e)}"
        )
```

---

## Step 4: Example API Usage

Once implemented, the endpoint will work like this:

### Basic Search
```
GET /search.data?q=nginx
```

Response:
```json
{
  "total": 12345,
  "page": 1,
  "results": [
    {
      "slug": "nginx",
      "star_count": 50000,
      "pull_count": "1B+",
      "publisher": {"name": "nginx"},
      "created_at": "2014-06-10T...",
      "updated_at": "2024-01-15T...",
      "short_description": "Official build of Nginx."
    }
  ]
}
```

### With Pagination and Sorting
```
GET /search.data?q=python&page=2&sortby=pull_count&order=desc
```

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `app/modules/search/search-dockerhub.py` | Rename + Modify | Rename to `search_dockerhub.py`, add async `search_dockerhub()` function |
| `app/modules/search/__init__.py` | Modify | Export the search function |
| `app/modules/api/api.py` | Modify | Add `/search.data` route with import |

---

## Testing

After implementation, verify with:

```bash
# Start the API server
uvicorn app.modules.api.api:app --reload

# Test basic search
curl "http://localhost:8000/search.data?q=yahoo"

# Test with pagination and sorting
curl "http://localhost:8000/search.data?q=yahoo&page=2&sortby=updated_at&order=desc"
```

---

## Questions Resolved

- **Response format:** Processed JSON (not raw pass-through)
- **Sort parameter:** Use `sortby` to match Docker Hub naming
