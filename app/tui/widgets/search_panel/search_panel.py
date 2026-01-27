"""
Search Panel Widget - Search Docker Hub and display results.

Contains:
- Search input field
- Search status display
- Results DataTable
- Pagination controls
"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Center
from textual.widgets import Static, Input, DataTable, Button


class SearchPanel(Static):
    """Search panel widget with search input, results table, and pagination."""
    
    def compose(self) -> ComposeResult:
        # Search widgets
        yield Static("Search Docker Hub", id="search-label")
        yield Input(
            placeholder="Enter search term...",
            id="search-input",
            type="text"
        )
        yield Static("", id="search-status")
        yield DataTable(id="results-table", cursor_type="row")
        # Pagination bar - AFTER the table so it appears below results
        with Center(id="pagination-container"):
            with Horizontal(id="pagination-bar"):
                yield Button("<<", id="btn-first")
                yield Button("<", id="btn-prev")
                yield Button(">", id="btn-next")
                yield Button(">>", id="btn-last")
                yield Static("Page 1 of -- (-- Results)", id="pagination-status")
    
    def setup_table(self) -> None:
        """Configure the results table columns. Call from app on_mount."""
        table = self.query_one("#results-table", DataTable)
        table.zebra_stripes = True
        table.add_column("SLUG", width=50)
        table.add_column("FAV", width=4)
        table.add_column("PULLS", width=6)
        table.add_column("UPDATED", width=12)
        table.add_column("DESCRIPTION", width=80)
