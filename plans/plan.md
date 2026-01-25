# TUI Enhancement Plan: Pagination Controls and Panel Alignment

## Overview

Add a pagination widget to the TUI that:
1. Shows current page position and total results
2. Provides navigation buttons (first/prev/next/last) and jump-to input
3. Aligns Left and Right panels horizontally by positioning it beneath tabs

---

## Current State Analysis

### Current Layout Structure ([`app.py`](app/tui/app.py:240-247))
```
Header
TopPanel (#top-panel)      <-- Search input lives here
  Horizontal (#main-content)
    LeftPanel (#left-panel)
      TabbedContent
        TabPane "Search Results"
          DataTable (#results-table)   <-- No pagination indicator
    RightPanel (#right-panel)
Footer
```

### Problem
- No visible pagination indicator
- Left panel header area (tabs) is shorter than Right panel header area (tabs + tag-select + repo-info)
- User cannot see: current page, total pages, total results

---

## Proposed Solution

### Desired Pagination Format
```
[<<] [<]  Page 1 / 3  (219 results)  [>] [>>]   Jump to: [___]
```

### Placement
- BENEATH the TabbedContent tabs
- ABOVE the #results-table widget
- This adds height to left panel header area, aligning it with right panel

### After Layout
```
+---------------------------------------------------------------+
|                          HEADER                               |
+---------------------------------------------------------------+
| [        search bar                                        ]  |
+-------------------------------+-------------------------------+
|      Search Results           |       Repo Overview           |
|-------------------------------|-------------------------------|
| [<<][<] Pg 1/3 (219) [>][>>]  | drichnerdisney/ollama - 1 tag |
| Jump to: [___]                | [  TAGS SELECT             ]  |
|-------------------------------|-------------------------------|
| SLUG | FAV | PULLS | UPDATED  | architecture: amd64           |
| ...  (scrollable rows)  ...   | os: linux                     |
|                               | ...                           |
+-------------------------------+-------------------------------+
```

---

## Implementation Details

### File: app/tui/app.py

#### 1. Add Button import ([line 14](app/tui/app.py:14))

```python
# BEFORE:
from textual.widgets import (
    Header, Footer, Static, Input, DataTable,
    TabbedContent, TabPane, Select
)

# AFTER:
from textual.widgets import (
    Header, Footer, Static, Input, DataTable,
    TabbedContent, TabPane, Select, Button
)
```

#### 2. Create PaginationBar widget class (insert after line 193, before RightPanel)

```python
class PaginationBar(Static):
    """Pagination controls for results table."""
    
    def compose(self) -> ComposeResult:
        with Horizontal(id="pagination-row"):
            yield Button("<<", id="first-page-btn", variant="default")
            yield Button("<", id="prev-page-btn", variant="default")
            yield Static("Page 0 / 0 (0 results)", id="page-indicator")
            yield Button(">", id="next-page-btn", variant="default")
            yield Button(">>", id="last-page-btn", variant="default")
        with Horizontal(id="jump-row"):
            yield Static("Jump to:", id="jump-label")
            yield Input(placeholder="", id="jump-input", type="integer")
```

#### 3. Modify LeftPanel class ([lines 186-193](app/tui/app.py:186-193))

```python
# BEFORE:
class LeftPanel(Static):
    """Left panel widget with tabbed content for search results."""
    
    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Search Results", id="search-results-tab"):
                yield DataTable(id="results-table", cursor_type="row")

# AFTER:
class LeftPanel(Static):
    """Left panel widget with tabbed content for search results."""
    
    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Search Results", id="search-results-tab"):
                yield PaginationBar(id="pagination-bar")
                yield DataTable(id="results-table", cursor_type="row")
```

#### 4. Add pagination button handler (insert after [line 289](app/tui/app.py:289))

```python
def on_button_pressed(self, event: Button.Pressed) -> None:
    """Handle pagination button clicks."""
    if not self.current_query:
        return
    
    results_per_page = 25  # Docker Hub default
    max_pages = (self.total_results + results_per_page - 1) // results_per_page if self.total_results > 0 else 1
    
    if event.button.id == "first-page-btn":
        if self.current_page > 1:
            self.fetch_page(self.current_query, 1, clear=True)
    elif event.button.id == "prev-page-btn":
        if self.current_page > 1:
            self.fetch_page(self.current_query, self.current_page - 1, clear=True)
    elif event.button.id == "next-page-btn":
        if self.current_page < max_pages:
            self.fetch_page(self.current_query, self.current_page + 1, clear=True)
    elif event.button.id == "last-page-btn":
        if self.current_page < max_pages:
            self.fetch_page(self.current_query, max_pages, clear=True)
```

#### 5. Add jump-to input handler (insert after button handler)

```python
def on_input_submitted(self, event: Input.Submitted) -> None:
    """Handle input submission - search or jump-to-page."""
    if event.input.id == "search-input":
        # Existing search logic
        query = event.value.strip()
        if not query:
            return
        self.current_query = query
        self.current_page = 1
        status = self.query_one("#search-status", Static)
        status.update(f"Searching for: {query}...")
        self.fetch_page(query, page=1, clear=True)
    
    elif event.input.id == "jump-input":
        # Jump to page logic
        if not self.current_query:
            return
        try:
            target_page = int(event.value.strip())
            results_per_page = 25
            max_pages = (self.total_results + results_per_page - 1) // results_per_page if self.total_results > 0 else 1
            if 1 <= target_page <= max_pages and target_page != self.current_page:
                self.fetch_page(self.current_query, target_page, clear=True)
            event.input.value = ""  # Clear input after jump
        except ValueError:
            pass
```

Note: This replaces the existing [`on_input_submitted`](app/tui/app.py:259-269) method with one that handles both search and jump inputs.

#### 6. Update pagination display in fetch_page (modify [lines 316-318](app/tui/app.py:316-318))

```python
# BEFORE:
self.current_page = page
self.total_results = total
status.update("")

# AFTER:
self.current_page = page
self.total_results = total
status.update("")

# Update pagination indicator
results_per_page = 25
max_pages = (total + results_per_page - 1) // results_per_page if total > 0 else 1
page_indicator = self.query_one("#page-indicator", Static)
page_indicator.update(f"Page {page} / {max_pages} ({total} results)")

# Enable/disable navigation buttons
first_btn = self.query_one("#first-page-btn", Button)
prev_btn = self.query_one("#prev-page-btn", Button)
next_btn = self.query_one("#next-page-btn", Button)
last_btn = self.query_one("#last-page-btn", Button)

first_btn.disabled = (page <= 1)
prev_btn.disabled = (page <= 1)
next_btn.disabled = (page >= max_pages)
last_btn.disabled = (page >= max_pages)
```

---

### File: app/tui/styles.tcss

#### 1. Add pagination bar styles (insert after [line 62](app/tui/styles.tcss:62))

```css
/* Pagination bar container */
#pagination-bar {
    height: auto;
    min-height: 4;
    padding: 0 1;
    background: $surface;
}

/* Pagination row with nav buttons */
#pagination-row {
    height: auto;
    align: center middle;
    padding: 0;
}

/* Jump-to row */
#jump-row {
    height: auto;
    align: left middle;
    padding: 0;
}

/* Page indicator text */
#page-indicator {
    width: auto;
    min-width: 24;
    text-align: center;
    padding: 0 1;
    color: $text;
}

/* Navigation buttons - thin styling */
#first-page-btn, #prev-page-btn, #next-page-btn, #last-page-btn {
    min-width: 4;
    width: 4;
    border: none;
    padding: 0;
    margin: 0 1;
}

#first-page-btn:disabled, #prev-page-btn:disabled,
#next-page-btn:disabled, #last-page-btn:disabled {
    opacity: 0.3;
}

/* Jump label */
#jump-label {
    width: auto;
    padding: 0 1;
    color: $text-muted;
}

/* Jump input - 3 character width */
#jump-input {
    width: 5;
    min-width: 5;
    max-width: 5;
}
```

---

## Summary of Changes

### app/tui/app.py

| Location | Change |
|----------|--------|
| [Line 14](app/tui/app.py:14) | Add `Button` to imports |
| After [line 193](app/tui/app.py:193) | Add `PaginationBar` class |
| [Lines 186-193](app/tui/app.py:186-193) | Modify `LeftPanel` to include `PaginationBar` |
| After [line 289](app/tui/app.py:289) | Add `on_button_pressed` handler |
| [Lines 259-269](app/tui/app.py:259-269) | Replace `on_input_submitted` to handle both search and jump |
| [Lines 316-318](app/tui/app.py:316-318) | Update pagination indicator and button states in `fetch_page` |

### app/tui/styles.tcss

| Location | Change |
|----------|--------|
| After [line 62](app/tui/styles.tcss:62) | Add pagination bar and component styles |

---

## Behavior Notes

1. **Button states**: First/Prev disabled on page 1; Next/Last disabled on last page
2. **Jump input**: 3-char width, integer-only, clears after successful jump
3. **Display format**: "Page X / Y (Z results)" where X=current, Y=total pages, Z=total results
4. **Page calculation**: `max_pages = ceil(total_results / 25)`
5. **Alignment**: The pagination bar adds height to left panel header area, aligning with right panel's tag-select + repo-info area
