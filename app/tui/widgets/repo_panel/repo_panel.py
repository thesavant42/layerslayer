"""
Repo Panel Widget - Display repository details and tag selection.

Contains:
- Repository info display
- Tag selection dropdown
- Config DataTable for tag details
"""

from textual.app import ComposeResult
from textual.widgets import Static, DataTable, Select


class RepoPanel(Static):
    """Repository panel widget with tag selection and config display."""
    
    def compose(self) -> ComposeResult:
        yield Static("Select a repository to view tags", id="repo-info")
        yield Select([], id="tag-select", prompt="Select a tag...")
        yield DataTable(id="config-table", cursor_type="row")
        yield Static("", id="right-panel-spacer")
    
    def setup_table(self) -> None:
        """Configure the config table. Call from app on_mount."""
        config_table = self.query_one("#config-table", DataTable)
        config_table.zebra_stripes = True
