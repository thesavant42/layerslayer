# Task 2 Plan: DataTable for Search Results

## Change 1: search_dockerhub.py

Current line 110 returns text:
```python
return format_results_text(results, total, page)
```

Change to return JSON:
```python
return {"results": results, "total": total, "page": page}
```

## Change 2: app.py

Replace LeftPanel Static with DataTable.

Current:
```python
yield LeftPanel("Search Results go Here", id="left-panel")
```

Change to:
```python
yield DataTable(id="results-table", cursor_type="row")
```

Add columns on mount:
```python
table = self.query_one("#results-table", DataTable)
table.add_columns("SLUG", "STARS", "PULLS", "UPDATED")
```

Populate from JSON in worker:
```python
data = response.json()
table.clear()
for r in data["results"]:
    table.add_row(r["id"], str(r["star_count"]), str(r["pull_count"]), r["updated_at"])
```

Done. Textual handles navigation.
