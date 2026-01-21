# Build Plan: /history API Endpoint

## Overview

Implement a FastAPI endpoint `/history` that queries the local SQLite database to display previously-peeked Docker image layers in formatted plain text.

**Source Requirements**: [peekHistory.md](peekHistory.md)

---

## Acceptance Criteria

Task is NOT COMPLETED until all criteria are met:

- [ ] 1. **FastAPI route**: `/history?q={query}&page={NaN}&page_size={NaN}&order={asc|desc}&sortby={column}`
- [ ] 2. Prints **FORMATTED TEXT**, NOT JSON
- [ ] 3. Results can be **sorted**
- [ ] 4. Results can be **paginated**
- [ ] 5. Results can be **filtered**

---

## Technical Specification

### Endpoint Definition

```
GET /history
```

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | None | Search filter - matches against owner, repo, or tag |
| `page` | int | 1 | Page number (1-indexed) |
| `page_size` | int | 30 | Results per page |
| `sortby` | string | `scraped_at` | Column to sort by |
| `order` | string | `desc` | Sort order: `asc` or `desc` |

### Valid `sortby` Values

- `scraped_at`
- `owner`
- `repo`
- `tag`
- `layer_index`
- `layer_size`

### Output Format

Plain text table with fixed-width columns:

```
| scraped_at   | owner                     | repo                      | tag                  | layer | size       |
|--------------|---------------------------|---------------------------|----------------------|-------|------------|
| 2026-01-14   | alpine                    | git                       | v2.52.0              | 1     | 31.7 MB    |
| 2026-01-14   | alpine                    | git                       | v2.52.0              | 2     | 93 B       |
```

**Column Width Constraints**:
- `scraped_at`: 12 chars (date only: YYYY-MM-DD)
- `owner`: max 25 chars (truncate with `...`)
- `repo`: max 25 chars (truncate with `...`)
- `tag`: max 20 chars (truncate with `...`)
- `layer_index`: 5 chars
- `layer_size`: human-readable format

### Response Headers

- `Content-Type: text/plain`
- Include pagination metadata in header or footer line

---

## Database Query

**Table**: `layer_metadata`

**Schema** (relevant columns):
```sql
layer_digest TEXT PRIMARY KEY,
image_ref TEXT,
owner TEXT,
repo TEXT,
tag TEXT,
layer_index INTEGER,
layer_size INTEGER,
scraped_at DATETIME
```

**Base Query Pattern**:
```sql
SELECT scraped_at, owner, repo, tag, layer_index, layer_size
FROM layer_metadata
WHERE (owner LIKE '%{q}%' OR repo LIKE '%{q}%' OR tag LIKE '%{q}%')  -- if q provided
ORDER BY {sortby} {order}
LIMIT {page_size} OFFSET {(page-1) * page_size}
```

---

## Implementation Tasks

### 1. Add imports and constants

**File**: [app/modules/api/api.py](../app/modules/api/api.py)

Add at the top of the file with other imports:

```python
import sqlite3

# Database path for history queries
DB_PATH = "app/data/lsng.db"

# Valid columns for sorting history results
HISTORY_SORTABLE_COLUMNS = ['scraped_at', 'owner', 'repo', 'tag', 'layer_index', 'layer_size']
```

---

### 2. Create helper functions

Add these helper functions before the endpoint definitions:

```python
def truncate_string(s: str, max_len: int) -> str:
    """Truncate string to max_len, adding '...' if truncated."""
    if s is None:
        return ""
    if len(s) <= max_len:
        return s
    return s[:max_len - 3] + "..."


def format_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    if size_bytes is None:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def format_history_table(rows: list, page: int, page_size: int, total_count: int) -> str:
    """
    Format database rows as a plain text table.
    
    Column widths:
    - scraped_at: 12 (date only)
    - owner: 25
    - repo: 25
    - tag: 20
    - layer_index: 5
    - layer_size: 10
    """
    # Header
    header = (
        f"| {'scraped_at':<12} | {'owner':<25} | {'repo':<25} | "
        f"{'tag':<20} | {'layer':<5} | {'size':<10} |"
    )
    separator = (
        f"|{'-'*14}|{'-'*27}|{'-'*27}|{'-'*22}|{'-'*7}|{'-'*12}|"
    )
    
    lines = [header, separator]
    
    for row in rows:
        # Extract and format date (first 10 chars of ISO timestamp)
        scraped = str(row['scraped_at'])[:10] if row['scraped_at'] else ""
        
        line = (
            f"| {scraped:<12} | "
            f"{truncate_string(row['owner'], 25):<25} | "
            f"{truncate_string(row['repo'], 25):<25} | "
            f"{truncate_string(row['tag'], 20):<20} | "
            f"{row['layer_index']:<5} | "
            f"{format_size(row['layer_size']):<10} |"
        )
        lines.append(line)
    
    # Pagination footer
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
    footer = f"\nPage {page} of {total_pages} | {total_count} total results"
    lines.append(footer)
    
    return "\n".join(lines)
```

---

### 3. Add the /history endpoint

Add this endpoint definition after the existing endpoints:

```python
@app.get("/history", response_class=PlainTextResponse)
def history(
    q: str = Query(default=None, description="Search filter for owner, repo, or tag"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=30, ge=1, le=100, description="Results per page"),
    sortby: str = Query(default="scraped_at", description="Column to sort by"),
    order: str = Query(default="desc", description="Sort order: asc or desc")
):
    """
    View history of previously-peeked Docker image layers.
    
    Returns formatted plain text table showing cached layer metadata
    from the local SQLite database.
    
    Example: /history?q=nginx&page=1&sortby=layer_size&order=desc
    """
    # Validate sortby column (prevent SQL injection)
    if sortby not in HISTORY_SORTABLE_COLUMNS:
        raise HTTPException(
            status_code=400,
            detail=f"sortby must be one of: {', '.join(HISTORY_SORTABLE_COLUMNS)}"
        )
    
    # Validate order
    if order not in ['asc', 'desc']:
        raise HTTPException(
            status_code=400,
            detail="order must be 'asc' or 'desc'"
        )
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build query with optional search filter
        base_columns = "scraped_at, owner, repo, tag, layer_index, layer_size"
        
        if q:
            # Search across owner, repo, and tag
            where_clause = "WHERE owner LIKE ? OR repo LIKE ? OR tag LIKE ?"
            search_param = f"%{q}%"
            params = [search_param, search_param, search_param]
            
            # Count total matching results
            count_query = f"SELECT COUNT(*) FROM layer_metadata {where_clause}"
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]
            
            # Fetch paginated results
            # Note: sortby is validated above, safe to interpolate
            data_query = (
                f"SELECT {base_columns} FROM layer_metadata "
                f"{where_clause} "
                f"ORDER BY {sortby} {order.upper()} "
                f"LIMIT ? OFFSET ?"
            )
            params.extend([page_size, (page - 1) * page_size])
            cursor.execute(data_query, params)
        else:
            # No search filter - return all results
            count_query = "SELECT COUNT(*) FROM layer_metadata"
            cursor.execute(count_query)
            total_count = cursor.fetchone()[0]
            
            data_query = (
                f"SELECT {base_columns} FROM layer_metadata "
                f"ORDER BY {sortby} {order.upper()} "
                f"LIMIT ? OFFSET ?"
            )
            cursor.execute(data_query, [page_size, (page - 1) * page_size])
        
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Handle empty results
        if not rows:
            if q:
                return f"No results found matching '{q}'\n"
            return "No cached layers found. Run a peek operation first.\n"
        
        return format_history_table(rows, page, page_size, total_count)
        
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
```

---

### 4. Integration Location

The new code should be added to [app/modules/api/api.py](../app/modules/api/api.py) in this order:

1. **Line ~9**: Add `import sqlite3` with other imports
2. **Line ~28**: Add `DB_PATH` and `HISTORY_SORTABLE_COLUMNS` constants after `IMAGE_PATTERN`
3. **Line ~30**: Add helper functions (`truncate_string`, `format_size`, `format_history_table`) before `@app.get("/peek")`
4. **After line 266**: Add the `/history` endpoint at the end of the file

---

## Architecture Diagram

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI as /history endpoint
    participant SQLite as lsng.db

    Client->>FastAPI: GET /history?q=nginx&page=1
    FastAPI->>FastAPI: Validate parameters
    FastAPI->>SQLite: SELECT with filters
    SQLite-->>FastAPI: Result rows
    FastAPI->>FastAPI: Format as text table
    FastAPI-->>Client: PlainTextResponse
```

---

## Example Requests and Expected Output

### Default request (last 30 results):
```bash
curl "http://127.0.0.1:8000/history"
```

### Search for alpine images:
```bash
curl "http://127.0.0.1:8000/history?q=alpine"
```

### Page 2, sorted by size descending:
```bash
curl "http://127.0.0.1:8000/history?page=2&sortby=layer_size&order=desc"
```

### Expected Output Format:
```
| scraped_at   | owner                     | repo                      | tag                  | layer | size       |
|--------------|---------------------------|---------------------------|----------------------|-------|------------|
| 2026-01-14   | alpine                    | git                       | v2.52.0              | 1     | 31.7 MB    |
| 2026-01-14   | alpine                    | git                       | v2.52.0              | 2     | 93.0 B     |
| 2026-01-14   | alpine                    | git                       | v2.52.0              | 0     | 3.1 MB     |

Page 1 of 1 | 3 total results
```

---

## Files to Modify

| File | Line | Changes |
|------|------|---------|
| [app/modules/api/api.py](../app/modules/api/api.py) | ~9 | Add `import sqlite3` |
| [app/modules/api/api.py](../app/modules/api/api.py) | ~28 | Add `DB_PATH` and `HISTORY_SORTABLE_COLUMNS` constants |
| [app/modules/api/api.py](../app/modules/api/api.py) | ~30 | Add helper functions before first endpoint |
| [app/modules/api/api.py](../app/modules/api/api.py) | EOF | Add `/history` endpoint at end of file |

---

## Testing Checklist

### Manual Testing via curl

```bash
# Test 1: Default request - should return last 30 results
curl "http://127.0.0.1:8000/history"

# Test 2: Pagination - page 2
curl "http://127.0.0.1:8000/history?page=2"

# Test 3: Search filter - should only show matching results
curl "http://127.0.0.1:8000/history?q=alpine"

# Test 4: Sort by layer_size descending
curl "http://127.0.0.1:8000/history?sortby=layer_size&order=desc"

# Test 5: Invalid sortby - should return 400
curl "http://127.0.0.1:8000/history?sortby=invalid_column"

# Test 6: Invalid order - should return 400
curl "http://127.0.0.1:8000/history?order=invalid"

# Test 7: Combined parameters
curl "http://127.0.0.1:8000/history?q=git&page=1&page_size=10&sortby=scraped_at&order=asc"
```

### Validation Criteria

- [ ] Response has `Content-Type: text/plain`
- [ ] Table header row displays correctly
- [ ] Column alignment is consistent
- [ ] Long owner/repo/tag values are truncated with `...`
- [ ] Layer size shows human-readable format (KB, MB, GB)
- [ ] Pagination footer shows correct page/total info
- [ ] Empty results show helpful message
- [ ] Invalid parameters return HTTP 400 with clear error message
