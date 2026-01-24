# Task 2 Plan: DataTable for Docker Hub Search Results

## Current State

### search_dockerhub.py (line 111)
Already changed to return JSON string:
```python
return json.dumps({"results": results, "total": total, "page": page})
```
API returns:
```json
{
    "page": 1,
    "results": [...],
    "total": 204
}
```

### app.py
DataTable with `cursor_type="row"` is in place. Columns added. But:
- Only requests page 1
- No pagination tracking
- No boundary detection for loading more pages

---

## What Needs To Be Done

### 1. app.py - Track Pagination State

Add instance variables to track:
```python
class DockerDorkerApp(App):
    current_query: str = ""
    current_page: int = 1
    total_results: int = 0
```

### 2. app.py - Update Worker to Store Pagination Info

In `search_docker_hub()` worker, after parsing response:
```python
data = response.json()
self.current_page = data["page"]
self.total_results = data["total"]
self.current_query = query
```

### 3. app.py - Boundary Detection for Next Page

Handle `DataTable.RowHighlighted` event. When cursor is on the last row and there are more results, load next page:

```python
def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
    table = self.query_one("#results-table", DataTable)
    
    # Check if cursor is on last row
    if event.cursor_row == table.row_count - 1:
        # Check if more results exist
        loaded_count = table.row_count
        if loaded_count < self.total_results:
            # Load next page
            self.load_next_page()

def load_next_page(self) -> None:
    self.current_page += 1
    self.fetch_page(self.current_query, self.current_page)
```

### 4. app.py - Separate Fetch Function That Appends Rows

Create `fetch_page()` that can either clear table (new search) or append (pagination):

```python
@work(exclusive=True)
async def fetch_page(self, query: str, page: int, clear: bool = False) -> None:
    table = self.query_one("#results-table", DataTable)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://127.0.0.1:8000/search.data",
            params={"q": query, "page": page, "sortby": "updated_at", "order": "desc"}
        )
        response.raise_for_status()
        data = response.json()
        
        self.current_page = data["page"]
        self.total_results = data["total"]
        
        if clear:
            table.clear()
        
        for r in data["results"]:
            table.add_row(
                r.get("id", ""),
                str(r.get("star_count", 0)),
                str(r.get("pull_count", "0")),
                r.get("updated_at", "")
            )
```

### 5. app.py - Update on_input_submitted

```python
def on_input_submitted(self, event: Input.Submitted) -> None:
    query = event.value.strip()
    if not query:
        return
    
    self.current_query = query
    self.current_page = 1
    self.fetch_page(query, page=1, clear=True)
```

---

## Summary of Changes

| File | Change |
|------|--------|
| search_dockerhub.py | Done - returns JSON string with results, total, page |
| app.py | Add pagination state variables |
| app.py | Add `on_data_table_row_highlighted()` for boundary detection |
| app.py | Add `fetch_page()` worker that can append rows |
| app.py | Update `on_input_submitted()` to use new fetch function |

---

## Data Flow

```
User types query -> on_input_submitted() 
    -> fetch_page(query, page=1, clear=True)
    -> API returns JSON
    -> Table cleared, rows added, pagination state saved

User navigates to last row -> on_data_table_row_highlighted()
    -> Checks if more results exist
    -> fetch_page(query, page=2, clear=False)
    -> API returns JSON
    -> Rows appended to existing table
```

Textual handles all navigation. No custom key bindings.
