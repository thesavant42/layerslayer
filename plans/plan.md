# TUI Enhancement Plan: Pagination Controls and Panel Alignment

## Overview

This plan addresses two main requirements:
1. Add visual page indicator and navigation buttons for pagination
2. Align Left and Right panels horizontally by relocating the search bar

---

## Current State Analysis

### Current Layout Structure (app.py lines 240-247)
```
Header
TopPanel (#top-panel) <-- Contains search input
  Horizontal (#main-content)
    LeftPanel (#left-panel)
    RightPanel (#right-panel)
Footer
```

### Issues Identified
- TopPanel creates vertical offset between Left/Right panel content
- No pagination indicator showing current page position
- No navigation buttons for page control (only keyboard-based at row boundaries)
- Dead space below results table in Left panel

---

## Proposed Changes

### 1. Relocate Search Widgets from TopPanel to LeftPanel

**File: app/tui/app.py**

#### Modify TopPanel class (lines 174-183)
```python
# BEFORE (lines 177-183):
def compose(self) -> ComposeResult:
    yield Input(
        placeholder="Search Docker Hub...",
        id="search-input",
        type="text"
    )
    yield Static("", id="search-status")

# AFTER:
def compose(self) -> ComposeResult:
    # TopPanel now empty - reserved for future use
    yield Static("", id="top-placeholder")
```

#### Modify LeftPanel class (lines 186-193)
```python
# BEFORE (lines 189-192):
def compose(self) -> ComposeResult:
    with TabbedContent():
        with TabPane("Search Results", id="search-results-tab"):
            yield DataTable(id="results-table", cursor_type="row")

# AFTER:
def compose(self) -> ComposeResult:
    # Search input moved here from TopPanel
    yield Input(
        placeholder="Search Docker Hub...",
        id="search-input",
        type="text"
    )
    yield Static("", id="search-status")
    with TabbedContent():
        with TabPane("Search Results", id="search-results-tab"):
            yield DataTable(id="results-table", cursor_type="row")
    # Pagination controls at bottom
    with Horizontal(id="pagination-controls"):
        yield Button("<< Prev", id="prev-page-btn", variant="default")
        yield Static("Page 0 of 0", id="page-indicator")
        yield Button("Next >>", id="next-page-btn", variant="default")
```

#### Add Button import (line 14)
```python
# BEFORE (lines 13-16):
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

---

### 2. Add Pagination Button Event Handlers

**File: app/tui/app.py**

#### Add button click handler (after line 289, in DockerDorkerApp class)
```python
def on_button_pressed(self, event: Button.Pressed) -> None:
    """Handle pagination button clicks."""
    if event.button.id == "prev-page-btn":
        if self.current_page > 1:
            self.fetch_page(self.current_query, self.current_page - 1, clear=True)
    elif event.button.id == "next-page-btn":
        results_per_page = 25  # Default Docker Hub page size
        max_pages = (self.total_results + results_per_page - 1) // results_per_page
        if self.current_page < max_pages:
            self.fetch_page(self.current_query, self.current_page + 1, clear=True)
```

#### Update page indicator in fetch_page method (after line 317)
```python
# BEFORE (lines 316-318):
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
page_indicator.update(f"Page {page} of {max_pages} ({total} results)")

# Enable/disable buttons based on position
prev_btn = self.query_one("#prev-page-btn", Button)
next_btn = self.query_one("#next-page-btn", Button)
prev_btn.disabled = (page <= 1)
next_btn.disabled = (page >= max_pages)
```

---

### 3. Style Changes

**File: app/tui/styles.tcss**

#### Reduce TopPanel height (lines 11-18)
```css
/* BEFORE: */
#top-panel {
    height: auto;
    min-height: 5;
    padding: 1 2;
    background: $surface;
    border: solid $primary;
    layout: vertical;
}

/* AFTER: */
#top-panel {
    height: 0;
    min-height: 0;
    padding: 0;
    display: none;
}
```

#### Add pagination control styles (add after line 62)
```css
/* Pagination controls container */
#pagination-controls {
    height: auto;
    min-height: 3;
    padding: 1;
    align: center middle;
    background: $surface;
}

/* Page indicator text */
#page-indicator {
    width: auto;
    min-width: 20;
    text-align: center;
    padding: 0 2;
    color: $text;
}

/* Pagination buttons */
#prev-page-btn, #next-page-btn {
    min-width: 10;
}

#prev-page-btn:disabled, #next-page-btn:disabled {
    opacity: 0.5;
}
```

#### Adjust left panel to accommodate search input (modify lines 39-47)
```css
/* BEFORE: */
#left-panel {
    width: 1fr;
    height: 100%;
    padding: 1 2;
    background: $surface;
    border: solid $secondary;
    overflow-y: auto;
}

/* AFTER: */
#left-panel {
    width: 1fr;
    height: 100%;
    padding: 1 2;
    background: $surface;
    border: solid $secondary;
    overflow-y: auto;
    layout: vertical;
}

/* Search input in left panel */
#left-panel #search-input {
    width: 100%;
    margin-bottom: 1;
}

#left-panel #search-status {
    height: auto;
    color: $text-muted;
    margin-bottom: 1;
}
```

---

## Visual Representation

### Before:
```
+---------------------------------------------------------------+
|                          HEADER                               |
+---------------------------------------------------------------+
| [        search bar                                        ]  |
| (status text)                                                 |
+-------------------------------+-------------------------------+
|      Search Results           |       Repo Overview           |
|-------------------------------|-------------------------------|
| SLUG | FAV | PULLS | UPDATED  | [  TAGS SELECT             ]  |
| ...  (scrollable rows)  ...   | architecture: amd64           |
|                               | os: linux                     |
|       (dead space)            | ...                           |
+-------------------------------+-------------------------------+
```

### After:
```
+---------------------------------------------------------------+
|                          HEADER                               |
+-------------------------------+-------------------------------+
| [   search bar             ]  | [  TAGS SELECT             ]  |
| (status text)                 | (repo info)                   |
|-------------------------------|-------------------------------|
|      Search Results           |       Repo Overview           |
|-------------------------------|-------------------------------|
| SLUG | FAV | PULLS | UPDATED  | architecture: amd64           |
| ...  (scrollable rows)  ...   | os: linux                     |
| ...  (more visible rows) ...  | ...                           |
|-------------------------------|                               |
| [<< Prev] Page 1 of 5 [Next>>]|                               |
+-------------------------------+-------------------------------+
```

---

## Summary of File Changes

### app/tui/app.py
| Location | Change |
|----------|--------|
| Line 14 | Add `Button` to imports |
| Lines 177-183 | Empty TopPanel compose method |
| Lines 189-192 | Restructure LeftPanel with search input and pagination |
| After line 289 | Add `on_button_pressed` handler |
| Lines 316-318 | Update pagination indicator in `fetch_page` |

### app/tui/styles.tcss
| Location | Change |
|----------|--------|
| Lines 11-18 | Hide TopPanel |
| Lines 39-47 | Add vertical layout to left-panel |
| After line 62 | Add pagination control styles |

---

## Implementation Notes

1. The pagination indicator updates automatically when results load
2. Previous/Next buttons disable at boundaries (page 1 and last page)
3. Keyboard navigation at row boundaries still works as before
4. TopPanel class remains but is hidden via CSS (preserves code structure)
5. Search input retains same ID so existing event handlers work unchanged

