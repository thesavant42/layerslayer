# History Tab Implementation Plan

## Overview
Add a History tab to the Right Panel that displays cached layer scrapes from the SQLite database and allows loading layer contents into the FS Simulator.

## Existing API
The `/history` endpoint already exists in `app/modules/api/api.py:118-185`:

```
GET http://localhost:8000/history?page=1&page_size=30&sortby=scraped_at&order=desc&q={query}
```

**Returns plain text table:**
```
scraped_at   | owner                     | repo                      | tag                  | idx  |   layer_size
-------------+---------------------------+---------------------------+----------------------+------+-------------
2026-01-27   | accurascan                | mrz                       | 38.0.0               | 0    |     76097157
```

## File Changes

### 1. Create `app/tui/widgets/history_panel/__init__.py`

```python
from .history_panel import HistoryPanel

__all__ = ["HistoryPanel"]
```

### 2. Create `app/tui/widgets/history_panel/history_panel.py`

```python
from textual.app import ComposeResult
from textual.containers import Horizontal, Center
from textual.widgets import Static, Input, DataTable, Button


class HistoryPanel(Static):
    """History panel widget showing cached layer scrapes."""
    
    def compose(self) -> ComposeResult:
        yield Static("Scrape History", id="history-label")
        yield Input(
            placeholder="Filter history...",
            id="history-filter-input",
            type="text"
        )
        yield Static("", id="history-status")
        yield DataTable(id="history-table", cursor_type="row")
        with Center(id="history-pagination-container"):
            with Horizontal(id="history-pagination-bar"):
                yield Button("<<", id="btn-history-first")
                yield Button("<", id="btn-history-prev")
                yield Button(">", id="btn-history-next")
                yield Button(">>", id="btn-history-last")
                yield Static("Page 1 of -- (-- Results)", id="history-pagination-status")
    
    def setup_table(self) -> None:
        """Configure the history table columns."""
        table = self.query_one("#history-table", DataTable)
        table.zebra_stripes = True
        table.add_column("DATE", width=12)
        table.add_column("OWNER", width=25)
        table.add_column("REPO", width=25)
        table.add_column("TAG", width=20)
        table.add_column("IDX", width=4)
        table.add_column("SIZE", width=12)
```

### 3. Create `app/tui/widgets/history_panel/styles.tcss`

Duplicates the pagination button styles from search_panel with history-specific IDs:

```css
#history-label {
    padding: 1 1;
    color: $accent;
    text-style: bold;
}

#history-filter-input {
    width: 100%;
    margin: 1 0;
}

#history-status {
    height: auto;
    color: $text-muted;
    padding: 0 1;
}

#history-table {
    height: 1fr;
    width: 100%;
    border: solid $primary;
    margin: 1;
}

#history-pagination-container {
    height: 3;
    width: 100%;
}

#history-pagination-bar {
    height: auto;
    width: auto;
}

#history-pagination-bar Button {
    border: round $primary;
    min-width: 4;
    margin: 0 0 0 0;
}

#history-pagination-status {
    margin-left: 2;
    color: $primary;
}
```

### 4. Update `app/tui/widgets/__init__.py`

Add HistoryPanel to exports:

```python
from .history_panel import HistoryPanel
```

And add to `__all__`:

```python
__all__ = [..., "HistoryPanel"]
```

### 5. Update `app/tui/app.py`

#### 5a. Add import

```python
from app.tui.widgets import SearchPanel, RepoPanel, FSSimulator, HistoryPanel, parse_fslog_line
```

#### 5b. Add CSS path in DockerDorkerApp.CSS_PATH

```python
CSS_PATH = [
    "styles.tcss",
    "modals/styles.tcss",
    "widgets/search_panel/styles.tcss",
    "widgets/repo_panel/styles.tcss",
    "widgets/fs_simulator/styles.tcss",
    "widgets/history_panel/styles.tcss",  # ADD THIS
]
```

#### 5c. Update RightPanel.compose() to add History tab

```python
class RightPanel(Static):
    """Right panel widget with tabbed content for image build details."""
    
    def compose(self) -> ComposeResult:
        with TabbedContent(id="right-tabs"):
            with TabPane("Repo Overview", id="repo-overview"):
                yield RepoPanel(id="repo-panel")
            with TabPane("History", id="history-tab"):
                yield HistoryPanel(id="history-panel")
```

#### 5d. Add history state variables in DockerDorkerApp

```python
# History state
history_query: str = ""
history_page: int = 1
history_total: int = 0
_loading_history: bool = False
```

#### 5e. Add history table setup in on_mount()

```python
def on_mount(self) -> None:
    # ... existing setup ...
    
    # Setup history table
    history_panel = self.query_one("#history-panel", HistoryPanel)
    history_panel.setup_table()
    
    # Load initial history
    self.fetch_history_page(page=1)
```

#### 5f. Add history input handler

Handle history filter input submission - check input id in on_input_submitted:

```python
def on_input_submitted(self, event: Input.Submitted) -> None:
    if event.input.id == "search-input":
        # existing search logic
        ...
    elif event.input.id == "history-filter-input":
        query = event.value.strip()
        self.history_query = query
        self.history_page = 1
        self.fetch_history_page(query=query, page=1, clear=True)
```

#### 5g. Add history fetch worker

```python
@work(exclusive=True, group="history")
async def fetch_history_page(self, query: str = "", page: int = 1, clear: bool = False) -> None:
    """Fetch history page from API."""
    self._loading_history = True
    status = self.query_one("#history-status", Static)
    table = self.query_one("#history-table", DataTable)
    
    try:
        async with httpx.AsyncClient() as client:
            params = {
                "page": page,
                "page_size": 30,
                "sortby": "scraped_at",
                "order": "desc"
            }
            if query:
                params["q"] = query
            
            response = await client.get(
                "http://127.0.0.1:8000/history",
                params=params
            )
            response.raise_for_status()
            
            # Parse plain text response
            lines = response.text.strip().split("\n")
            
            self.history_page = page
            status.update("")
            self.update_history_pagination()
            
            if clear:
                table.clear()
            
            # Skip header and separator lines (first 2 lines)
            for line in lines[2:]:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 6:
                    table.add_row(
                        parts[0],  # scraped_at
                        parts[1],  # owner
                        parts[2],  # repo
                        parts[3],  # tag
                        parts[4],  # idx
                        parts[5],  # layer_size
                    )
    except httpx.RequestError as e:
        status.update(f"Request error: {e}")
    except httpx.HTTPStatusError as e:
        status.update(f"HTTP error: {e.response.status_code}")
    finally:
        self._loading_history = False
```

#### 5h. Add history pagination display updater

```python
def update_history_pagination(self) -> None:
    """Update history pagination status."""
    status = self.query_one("#history-pagination-status", Static)
    table = self.query_one("#history-table", DataTable)
    row_count = table.row_count
    # Estimate total pages based on results
    status.update(f"Page {self.history_page} ({row_count} results)")
```

#### 5i. Add history pagination button handler

Add to on_button_pressed():

```python
def on_button_pressed(self, event: Button.Pressed) -> None:
    # ... existing pagination logic ...
    
    # History pagination
    if event.button.id == "btn-history-first":
        self.fetch_history_page(query=self.history_query, page=1, clear=True)
    elif event.button.id == "btn-history-prev":
        if self.history_page > 1:
            self.fetch_history_page(query=self.history_query, page=self.history_page - 1, clear=True)
    elif event.button.id == "btn-history-next":
        self.fetch_history_page(query=self.history_query, page=self.history_page + 1, clear=True)
    elif event.button.id == "btn-history-last":
        # Just go forward since we don't know total
        self.fetch_history_page(query=self.history_query, page=self.history_page + 1, clear=True)
```

#### 5j. Add history row selection handler

Add to on_data_table_row_selected():

```python
def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
    # ... existing handlers ...
    
    elif table.id == "history-table":
        self._handle_history_row_selection(row_data)
```

Add new method:

```python
def _handle_history_row_selection(self, row_data: tuple) -> None:
    """Handle selection in history-table to load layer into FS Simulator."""
    if len(row_data) < 5:
        return
    
    owner = str(row_data[1]).strip()
    repo = str(row_data[2]).strip()
    tag = str(row_data[3]).strip()
    idx_str = str(row_data[4]).strip()
    
    try:
        layer_idx = int(idx_str)
    except ValueError:
        return
    
    # Set state for FS Simulator
    self.selected_namespace = owner
    self.selected_repo = repo
    self.selected_tag = tag
    self.fs_image = f"{owner}/{repo}:{tag}"
    self.fs_path = "/"
    self.fs_layer = layer_idx
    
    # Update status and switch to FS Simulator tab
    fs_status = self.query_one("#fs-status", Static)
    fs_status.update(f"Loading {self.fs_image} layer {layer_idx} from history...")
    
    left_tabs = self.query_one("#left-tabs", TabbedContent)
    left_tabs.active = "fs-simulator-tab"
    
    # Load the layer
    self.check_and_load_fslog()
```

## Summary of Changes

| File | Action |
|------|--------|
| `app/tui/widgets/history_panel/__init__.py` | CREATE |
| `app/tui/widgets/history_panel/history_panel.py` | CREATE |
| `app/tui/widgets/history_panel/styles.tcss` | CREATE |
| `app/tui/widgets/__init__.py` | MODIFY - add HistoryPanel export |
| `app/tui/app.py` | MODIFY - add tab, state, handlers |

## Testing

1. Start the API server: `uvicorn app.modules.api.api:app --reload`
2. Run the TUI: `python -m app.tui.app`
3. Navigate to "History" tab in right panel
4. Verify history data loads
5. Test filter input
6. Test pagination buttons
7. Click a history row and verify FS Simulator loads the layer
