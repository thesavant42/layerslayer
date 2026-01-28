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
