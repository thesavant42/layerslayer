

![current state of tui](/plans/image.png)

I need a pagination tracker for the #results-table widget, to keep track of which page of how many results am I presently on?

## Background:

Pagination for #results-table is handled by responses from an upstream API; we fetch the next or previous pages' results by navigating the data table.

The TUI tracks pagination using class attributes defined at lines 229-233:

```python
# Pagination state
current_query: str = ""
current_page: int = 1
total_results: int = 0
_loading_page: bool = False
```
It tracks:

`current_page` - The page number (1-indexed)
`total_results` - Total number of results, not pages

How it uses them:

In `fetch_page()`, after getting API response:

```python
self.current_page = page
self.total_results = total
```


In `on_key()`, to check if next page exists:


```python
elif event.key == "down" and table.cursor_row == table.row_count - 1:
    if table.row_count < self.total_results:
        self.fetch_page(self.current_query, self.current_page + 1, clear=True)
```

The logic compares `table.row_count` (rows displayed) against `total_results` to determine if more pages exist. It does not calculate or track the total number of pages.

## Problem Statement

There's no visible way for the user to know:
    - how many total results have been returned,
    - how many results are being displayed per page (30)
    - how many pages of results total are there
    - Which page number is the user currently viewing?

### Constraints
- `search.data` returns the pagination links within the json response body of search result responses
    - json response fro search results is received verbatim as sent from the upstream API server


## Desired Outcome:

- Pagination Markers and a way to jumpt o results,for example:

    `< <  page 1  / 3  (219 results) > >   Jump to: [2]` 

- Where the < < and > > symbols represent glyphs to page 1 page forward or backward, or jump to first page or last page
    - Should be [buttons](/plans/docs/button.md) with a thin styling with text labels
    - Text input box, with 3 character width to jump to a specific page of results

### Placement in TUI

I would like the pagination widget to be placed :
    - BENEATH the `tabbedcontent` tabs
    - ABOVE the #results-table widget
    - So that the pagination widget causes the #results-table to be positioned lower in the screen, and brings the two panels into visual alginment.



- Visual Example of the current panel misalignment:

![current state of tui](/plans/image.png)