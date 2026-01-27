# TUI Refactoring Plan

## Overview

The [`app/tui/app.py`](app/tui/app.py) file has grown to 1093 lines and [`app/tui/styles.tcss`](app/tui/styles.tcss) to 262 lines. This plan breaks these monolithic files into logical submodules for better maintainability, testability, and code organization.

## Current State Analysis

### app.py Breakdown (1093 lines)

| Section | Lines | Description |
|---------|-------|-------------|
| Imports | 1-36 | Standard library and Textual imports |
| Formatters | 38-200 | 5 utility functions for data formatting |
| Widgets | 203-367 | 3 panel/modal widget classes |
| App Class | 369-1089 | Main DockerDorkerApp with all handlers |

### Key Components to Extract

**Utility Functions:**
- [`format_history_date()`](app/tui/app.py:38) - ISO date to MM-DD-YYYY
- [`flatten_nested()`](app/tui/app.py:60) - Dict/list flattening with dot notation
- [`is_binary_content()`](app/tui/app.py:94) - Binary content detection
- [`format_config()`](app/tui/app.py:119) - OCI config JSON formatting
- [`parse_slug()`](app/tui/app.py:353) - Repository slug parsing

**Widget Classes:**
- [`LeftPanel`](app/tui/app.py:203) - Search results + FS Simulator tabs
- [`RightPanel`](app/tui/app.py:233) - Repo overview + tag selection
- [`FileActionModal`](app/tui/app.py:245) - File action chooser modal
- [`TextViewerModal`](app/tui/app.py:277) - Text content viewer modal
- [`SaveFileModal`](app/tui/app.py:303) - Save filename modal

### styles.tcss Breakdown (262 lines)

| Section | Lines | Description |
|---------|-------|-------------|
| Search styles | 9-27 | Search label, input, status |
| Layout | 31-47 | Main content, left panel base |
| Search Results | 49-87 | Results table, pagination |
| Right Panel | 89-119 | Repo info, tag select, config table |
| Footer | 121-124 | Footer dock |
| FS Simulator | 126-151 | FS status, breadcrumb, table, spacer |
| Modals | 153-262 | FileActionModal, TextViewerModal, SaveFileModal |

---

## Proposed Directory Structure

```
app/tui/
├── app.py                      # Slim main app - imports, compose, event routing
├── styles.tcss                 # Core layout only - header, footer, main-content
├── __init__.py                 # Package init
│
├── utils/
│   ├── __init__.py             # Export all formatters
│   └── formatters.py           # All utility/formatting functions
│
├── modals/
│   ├── __init__.py             # Export all modal classes
│   ├── file_action.py          # FileActionModal class
│   ├── text_viewer.py          # TextViewerModal class
│   ├── save_file.py            # SaveFileModal class
│   └── styles.tcss             # All modal styles consolidated
│
└── widgets/
    ├── __init__.py             # Export widget classes
    │
    ├── search_panel/
    │   ├── __init__.py         # Export SearchPanel
    │   ├── search_panel.py     # LeftPanel renamed to SearchPanel
    │   └── styles.tcss         # Search input, results table, pagination
    │
    ├── repo_panel/
    │   ├── __init__.py         # Export RepoPanel
    │   ├── repo_panel.py       # RightPanel renamed to RepoPanel
    │   └── styles.tcss         # Repo info, tag select, config table
    │
    └── fs_simulator/
        ├── __init__.py         # Export FSSimulator
        ├── fs_simulator.py     # FS browser component extracted
        └── styles.tcss         # FS status, breadcrumb, table
```

---

## Refactoring Steps

### Step 1: Create Utils Module

**File:** `app/tui/utils/formatters.py`

Extract these functions from app.py:
- `format_history_date(iso_date: str) -> str`
- `flatten_nested(obj: dict | list, prefix: str = "") -> list[tuple[str, str]]`
- `is_binary_content(content: str) -> bool`
- `format_config(config: dict) -> list[tuple[str, str]]`
- `parse_slug(slug: str) -> tuple[str, str]`

**File:** `app/tui/utils/__init__.py`
```python
from .formatters import (
    format_history_date,
    flatten_nested,
    is_binary_content,
    format_config,
    parse_slug
)
```

### Step 2: Create Modals Submodule

**File:** `app/tui/modals/file_action.py`
- Extract `FileActionModal` class
- Self-contained with its own imports

**File:** `app/tui/modals/text_viewer.py`
- Extract `TextViewerModal` class

**File:** `app/tui/modals/save_file.py`
- Extract `SaveFileModal` class

**File:** `app/tui/modals/styles.tcss`
- Move lines 153-262 from main styles.tcss
- FileActionModal styles
- TextViewerModal styles
- SaveFileModal styles

**File:** `app/tui/modals/__init__.py`
```python
from .file_action import FileActionModal
from .text_viewer import TextViewerModal
from .save_file import SaveFileModal
```

### Step 3: Refactor Search Panel Widget

**File:** `app/tui/widgets/search_panel/search_panel.py`
- Rename `LeftPanel` to `SearchPanel`
- Keep the compose() method with TabbedContent
- Move search-related event handlers as methods

**File:** `app/tui/widgets/search_panel/styles.tcss`
- Move search label, input, status styles (lines 9-27)
- Move results table styles (lines 49-64)
- Move pagination styles (lines 66-87)
- Move search-results-tab styles (lines 49-51)

### Step 4: Refactor Repo Panel Widget

**File:** `app/tui/widgets/repo_panel/repo_panel.py`
- Rename `RightPanel` to `RepoPanel`
- Keep compose() with TabbedContent for Repo Overview
- Move tag-related handlers as methods

**File:** `app/tui/widgets/repo_panel/styles.tcss`
- Move right panel styles (lines 89-119)

### Step 5: Create FS Simulator Widget

**File:** `app/tui/widgets/fs_simulator/fs_simulator.py`
- Extract FS Simulator content as a reusable component
- Contains the DataTable and status widgets
- Move `_parse_fslog_line()` method here

**File:** `app/tui/widgets/fs_simulator/styles.tcss`
- Move FS simulator styles (lines 126-151)

### Step 6: Slim Down Main app.py

The main app.py should become approximately 200-300 lines containing:
- Imports from submodules
- DockerDorkerApp class with:
  - CSS_PATH pointing to main styles.tcss
  - compose() yielding Header, SearchPanel, RepoPanel, Footer
  - High-level event routing that delegates to widget methods
  - Worker methods for API calls

### Step 7: Update Core styles.tcss

Keep only core layout styles:
- Main content horizontal split
- Left/right panel base sizing
- Footer dock
- DataTable header styling (shared)

---

## File Movement Summary

| From | To |
|------|-----|
| app.py lines 38-92 | utils/formatters.py |
| app.py lines 119-200 | utils/formatters.py |
| app.py lines 353-367 | utils/formatters.py |
| app.py lines 245-275 | modals/file_action.py |
| app.py lines 277-301 | modals/text_viewer.py |
| app.py lines 303-351 | modals/save_file.py |
| app.py lines 203-231 | widgets/search_panel/search_panel.py |
| app.py lines 233-243 | widgets/repo_panel/repo_panel.py |
| styles.tcss lines 153-262 | modals/styles.tcss |
| styles.tcss lines 9-87 | widgets/search_panel/styles.tcss |
| styles.tcss lines 89-119 | widgets/repo_panel/styles.tcss |
| styles.tcss lines 126-151 | widgets/fs_simulator/styles.tcss |

---

## CSS Loading Strategy

Textual supports loading multiple CSS files. Each widget can specify its own CSS_PATH and they get merged:

**Option A: Widget-level CSS_PATH**
```python
class SearchPanel(Static):
    CSS_PATH = "styles.tcss"  # Relative to the module
```

**Option B: App-level CSS aggregation**
```python
class DockerDorkerApp(App):
    CSS_PATH = [
        "styles.tcss",
        "modals/styles.tcss",
        "widgets/search_panel/styles.tcss",
        "widgets/repo_panel/styles.tcss",
        "widgets/fs_simulator/styles.tcss",
    ]
```

Recommendation: Use Option B for explicit control and easier debugging.

---

## Import Structure After Refactoring

**app.py:**
```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Header, Footer

from app.tui.utils import parse_slug, format_config, is_binary_content
from app.tui.modals import FileActionModal, TextViewerModal, SaveFileModal
from app.tui.widgets.search_panel import SearchPanel
from app.tui.widgets.repo_panel import RepoPanel
```

---

## Expected Results

| Metric | Before | After |
|--------|--------|-------|
| app.py lines | 1093 | ~250-350 |
| styles.tcss lines | 262 | ~50 |
| Number of files | 2 | ~15 |
| Testability | Low | High (isolated modules) |
| Reusability | Low | High (widgets can be reused) |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Circular imports | Keep utils independent, modals import from utils, widgets import from utils and modals |
| CSS specificity conflicts | Use unique IDs and class prefixes per widget |
| Event bubbling issues | Test each widget independently before integration |
| Path resolution for CSS | Use pathlib for reliable relative paths |

---

## Execution Order

1. Create utils/formatters.py and verify imports work
2. Create modals/ submodule with all three modals
3. Create widgets/search_panel/ 
4. Create widgets/repo_panel/
5. Create widgets/fs_simulator/
6. Update main app.py to import and compose
7. Split styles.tcss and update CSS_PATH
8. Test full application flow
9. Clean up empty placeholder files

---

## Notes

- The existing empty files in widgets/ subdirectories will be replaced
- The existing empty files in utils/ will be replaced  
- Consider adding `__all__` exports to each `__init__.py` for explicit API
- Add type hints throughout for better IDE support
