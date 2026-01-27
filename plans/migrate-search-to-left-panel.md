# Implementation Plan: Migrate Search to Left Panel

## Overview
Move the search Input and search-status widgets from TopPanel into LeftPanel, then remove TopPanel entirely.

---

## Additional Fixes (from user feedback on screenshot)

### Issue 1: Missing "Search Docker Hub" Label
The green arrow in the screenshot shows that a text label "Search Docker Hub" should appear above the search input.

**Change in `app/tui/app.py` line 209:**
Add a Static label before the Input widget:
```python
yield Static("Search Docker Hub", id="search-label")
```

### Issue 2: Pagination Bar Outside Panel
The yellow arrow shows the pagination bar at the very bottom of the screen, outside the left panel border. It should be BEFORE the DataTable, not after.

**Change in `app/tui/app.py` lines 215-222:**
Move the `#pagination-bar` Horizontal container BEFORE the DataTable:
```python
# Current order:
#   Input
#   Static (status)
#   DataTable       <-- problem: pagination comes after
#   Horizontal (pagination)

# Fixed order:
#   Static (label)
#   Input
#   Static (status)
#   Horizontal (pagination)  <-- move pagination here
#   DataTable
```

### Issue 3: CSS for search-label
Add styling for the new label in `app/tui/styles.tcss`:
```css
#search-label {
    padding: 0 1;
    color: $accent;
    text-style: bold;
}
```

## Files to Modify
1. `app/tui/app.py`
2. `app/tui/styles.tcss`

---

## Changes for `app/tui/app.py`

### Change 1: Modify LeftPanel.compose() (lines 218-232)

**Current code:**
```python
class LeftPanel(Static):
    """Left panel widget with tabbed content for search results and FS simulator."""
    
    def compose(self) -> ComposeResult:
        with TabbedContent(id="left-tabs"):
            with TabPane("Search Results", id="search-results-tab"):
                yield Static("", id="left-spacer")
                yield DataTable(id="results-table", cursor_type="row")
                with Horizontal(id="pagination-bar"):
                    yield Button("<<", id="btn-first")
                    yield Button("<", id="btn-prev")
                    yield Button(">", id="btn-next")
                    yield Button(">>", id="btn-last")
                    yield Static("Page 1 of -- (-- Results)", id="pagination-status")
            with TabPane("FS Simulator", id="fs-simulator-tab"):
                yield Static("Select a layer from config to browse filesystem", id="fs-status")
                yield Static("Path: /", id="fs-breadcrumb")
                yield DataTable(id="fs-table", cursor_type="row")
```

**New code:**
```python
class LeftPanel(Static):
    """Left panel widget with search input and tabbed content for results/FS simulator."""
    
    def compose(self) -> ComposeResult:
        # Search widgets (migrated from TopPanel)
        yield Input(
            placeholder="Search Docker Hub...",
            id="search-input",
            type="text"
        )
        yield Static("", id="search-status")
        
        with TabbedContent(id="left-tabs"):
            with TabPane("Search Results", id="search-results-tab"):
                yield DataTable(id="results-table", cursor_type="row")
                with Horizontal(id="pagination-bar"):
                    yield Button("<<", id="btn-first")
                    yield Button("<", id="btn-prev")
                    yield Button(">", id="btn-next")
                    yield Button(">>", id="btn-last")
                    yield Static("Page 1 of -- (-- Results)", id="pagination-status")
            with TabPane("FS Simulator", id="fs-simulator-tab"):
                yield Static("Select a layer from config to browse filesystem", id="fs-status")
                yield Static("Path: /", id="fs-breadcrumb")
                yield DataTable(id="fs-table", cursor_type="row")
```

**Key changes:**
- Add `Input` and `Static` for search at the top of LeftPanel (before TabbedContent)
- Remove `yield Static("", id="left-spacer")` from inside the TabPane

---

### Change 2: Remove TopPanel class entirely (lines 203-212)

**Delete these lines:**
```python
class TopPanel(Static):
    """Top panel widget with search input."""
    # Do not set height to 0 Do not Collapse Do NOT delete!
    def compose(self) -> ComposeResult:
        yield Input(
            placeholder="Search Docker Hub...",
            id="search-input",
            type="text"
        )
        yield Static("", id="search-status")
```

---

### Change 3: Update DockerDorkerApp.compose() (lines 395-402)

**Current code:**
```python
def compose(self) -> ComposeResult:
    """Compose the UI layout."""
    yield Header(show_clock=True)
    yield TopPanel(id="top-panel")
    with Horizontal(id="main-content"):
        yield LeftPanel(id="left-panel")
        yield RightPanel(id="right-panel")
    yield Footer()
```

**New code:**
```python
def compose(self) -> ComposeResult:
    """Compose the UI layout."""
    yield Header(show_clock=True)
    with Horizontal(id="main-content"):
        yield LeftPanel(id="left-panel")
        yield RightPanel(id="right-panel")
    yield Footer()
```

---

### Change 4: Update module docstring (lines 1-9)

**Current:**
```python
"""
dockerDorkerUI

A basic UI structure with:
- Header (docked top)
- Top Panel (1/3) with search input
- Left/Right Panels (50/50 split, 2/3 height)
- Footer (docked bottom)
"""
```

**New:**
```python
"""
dockerDorkerUI

A basic UI structure with:
- Header (docked top)
- Left Panel with search input and tabbed results/FS simulator
- Right Panel with repo overview and tag selection
- Footer (docked bottom)
"""
```

---

## Changes for `app/tui/styles.tcss`

### Change 1: Remove #top-panel styles (lines 9-18)

**Delete these lines:**
```css
/* TODO When search is fully migrated to the Left Panel, the top Panel will not be needed
/* Top panel - flows below header in vertical layout (not docked) */
#top-panel {
    height: auto;
    min-height: 5;
    padding: 1 2;
    background: $surface;
    border: solid $primary;
    layout: vertical;
}
```

---

### Change 2: Update search widget styles (lines 20-31)

**Current:**
```css
/* TODO Move #search-input and #search-status to the space currently occupied by #left-spacer
/* Search input styling */
#search-input {
    width: 100%;
    margin-bottom: 1;
}

/* Search status text */
#search-status {
    height: auto;
    color: $text-muted;
}
```

**New:**
```css
/* Search input styling - now in LeftPanel */
#search-input {
    width: 100%;
    margin: 1;
}

/* Search status text - now in LeftPanel */
#search-status {
    height: auto;
    color: $text-muted;
    padding: 0 1;
}
```

---

### Change 3: Remove #left-spacer styles (lines 58-62)

**Delete these lines:**
```css
/* TODO Move search input Widget to the space occupied by #left-spacer
/* Spacer to align with right panel widgets */
#left-spacer {
    height: 9;
}
```

---

## Summary of Line Changes

| File | Action | Lines |
|------|--------|-------|
| `app.py` | Delete TopPanel class | 203-212 |
| `app.py` | Remove TopPanel yield | 398 |
| `app.py` | Modify LeftPanel.compose() | 218-232 |
| `app.py` | Update docstring | 1-9 |
| `styles.tcss` | Delete #top-panel rules | 9-18 |
| `styles.tcss` | Update #search-input/#search-status | 20-31 |
| `styles.tcss` | Delete #left-spacer rules | 58-62 |

---

## Verification Steps

After implementation:
1. Run the TUI app: `python -m app.tui.app` or `python main.py`
2. Verify search input appears at top of left panel
3. Verify search functionality still works (type query, press Enter)
4. Verify search status updates correctly
5. Verify no visual gap where TopPanel used to be
6. Verify left/right panels are visually balanced
