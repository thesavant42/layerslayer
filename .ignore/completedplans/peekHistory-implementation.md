# Implementation Plan: /history Endpoint

## Overview

Add a `/history` endpoint to query cached scan results from the `layer_metadata` table.

**Files to modify:**
1. `app/modules/keepers/storage.py` - Add query function
2. `app/modules/api/api.py` - Add FastAPI route

---

## 1. storage.py - Query Function

**Location:** Line 524-526 (replace the TODO comment)

**Function signature:**
```python
def get_history(
    conn: sqlite3.Connection,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 30,
    sortby: str = "scraped_at",
    order: str = "desc",
) -> list[dict]:
```

**Columns to select:** `scraped_at`, `owner`, `repo`, `tag`, `layer_index`, `layer_size`

**Valid sortby columns:** `scraped_at`, `owner`, `repo`, `tag`, `layer_index`, `layer_size`

**Query logic:**
- Base query selects the 6 required columns from `layer_metadata`
- If `q` is provided, add WHERE clause: `owner LIKE %q% OR repo LIKE %q% OR tag LIKE %q%`
- Apply ORDER BY using `sortby` and `order` parameters
- Apply LIMIT and OFFSET for pagination: `LIMIT page_size OFFSET (page - 1) * page_size`

**Returns:** List of dicts with the queried rows

---

## 2. api.py - FastAPI Route

**Route:** `GET /history`

**Query parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| q | str | None | Filter by owner, repo, or tag |
| page | int | 1 | Page number |
| page_size | int | 30 | Results per page |
| sortby | str | scraped_at | Column to sort by |
| order | str | desc | Sort order: asc or desc |

**Response:** `PlainTextResponse` with formatted text table

**Column widths:**
| Column | Width |
|--------|-------|
| scraped_at | 12 chars |
| owner | 25 chars max |
| repo | 25 chars max |
| tag | 20 chars max |
| layer_index | 4 chars |
| layer_size | variable |

**Format example:**
```
scraped_at   | owner                     | repo                      | tag                  | idx  | layer_size
-------------|---------------------------|---------------------------|----------------------|------|------------
2025-01-15   | nginx                     | nginx                     | latest               | 0    | 12345678
2025-01-14   | library                   | alpine                    | 3.19                 | 1    | 9876543
```

**Implementation notes:**
- Import `init_database` and `get_history` from `app.modules.keepers.storage`
- Validate `sortby` against allowed columns
- Validate `order` is `asc` or `desc`
- Truncate long strings with `...` if they exceed column width
- Format `scraped_at` to show just the date portion (first 10 chars of ISO format)

---

## Database Schema Reference

From `layer_metadata` table:
- `scraped_at` - DATETIME
- `owner` - TEXT
- `repo` - TEXT  
- `tag` - TEXT
- `layer_index` - INTEGER
- `layer_size` - INTEGER

---

## Acceptance Criteria Mapping

| Criteria | Implementation |
|----------|----------------|
| FastAPI route with all params | `/history?q=&page=&page_size=&order=&sortby=` |
| Formatted text output | PlainTextResponse with column-aligned rows |
| Sortable results | ORDER BY with sortby and order params |
| Paginated results | LIMIT/OFFSET with page and page_size params |
| Filterable results | WHERE clause with LIKE on owner/repo/tag |
