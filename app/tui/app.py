"""
dockerDorkerUI

A basic UI structure with:
- Header (docked top)
- Top Panel (1/3) with search input
- Left/Right Panels (50/50 split, 2/3 height)
- Footer (docked bottom)
"""

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Header, Footer, Static, Input, DataTable
from textual.binding import Binding
from textual import work
import httpx
import sys
from pathlib import Path

# Add project root to path for imports when running directly
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import parsing functions for raw Docker Hub format
from app.modules.search.search_dockerhub import get_results, format_date


class TopPanel(Static):
    """Top panel widget with search input."""
    
    def compose(self) -> ComposeResult:
        yield Input(
            placeholder="Search Docker Hub...",
            id="search-input",
            type="text"
        )
        yield Static("", id="search-status")


class LeftPanel(Static):
    """Left panel widget (50% width)."""
    pass


class RightPanel(Static):
    """Right panel widget (50% width)."""
    pass


class DockerDorkerApp(App):
    """dockerDorker - A Textual app with a basic UI layout."""

    CSS_PATH = "styles.tcss"
    TITLE = "dockerDorker"
    SUB_TITLE = "by @thesavant42"

    # Pagination state
    current_query: str = ""
    current_page: int = 1
    total_results: int = 0
    _loading_page: bool = False  # Flag to prevent pagination loops

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header(show_clock=True)
        yield TopPanel(id="top-panel")
        with Horizontal(id="main-content"):
            yield DataTable(id="results-table", cursor_type="row")
            yield RightPanel("Right Panel", id="right-panel")
        yield Footer()

    def on_mount(self) -> None:
        """Set the Dracula theme when the app mounts."""
        self.theme = "dracula"
        table = self.query_one("#results-table", DataTable)
        table.add_column("SLUG", width=50)
        table.add_column("FAV", width=4)
        table.add_column("PULLS", width=8)
        table.add_column("UPDATED", width=12)
        table.add_column("DESCRIPTION", width=80)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input submission."""
        query = event.value.strip()
        if not query:
            return
        
        self.current_query = query
        self.current_page = 1
        status = self.query_one("#search-status", Static)
        status.update(f"Searching for: {query}...")
        self.fetch_page(query, page=1, clear=True)

    def on_key(self, event) -> None:
        """Handle key events for pagination at boundaries."""
        if self._loading_page:
            return
        
        table = self.query_one("#results-table", DataTable)
        if not table.has_focus:
            return
        
        # UP at row 0 -> previous page
        if event.key == "up" and table.cursor_row == 0 and self.current_page > 1:
            self.fetch_page(self.current_query, self.current_page - 1, clear=True)
            event.prevent_default()
        
        # DOWN at last row -> next page
        elif event.key == "down" and table.cursor_row == table.row_count - 1:
            if table.row_count < self.total_results:
                self.fetch_page(self.current_query, self.current_page + 1, clear=True)
                event.prevent_default()

    @work(exclusive=True)
    async def fetch_page(self, query: str, page: int, clear: bool = False) -> None:
        """Worker to fetch a page of results."""
        self._loading_page = True
        status = self.query_one("#search-status", Static)
        table = self.query_one("#results-table", DataTable)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://127.0.0.1:8000/search.data",
                    params={
                        "q": query,
                        "page": page,
                        "sort": "updated_at",
                        "order": "desc"
                    }
                )
                response.raise_for_status()
                
                # Parse raw Docker Hub flat array format
                data = response.json()
                results, total = get_results(data)
                
                # Use the page parameter we sent, total from results
                self.current_page = page
                self.total_results = total
                status.update("")
                
                if clear:
                    table.clear()
                
                for r in results:
                    table.add_row(
                        r.get("id", ""),
                        str(r.get("star_count", 0)),
                        str(r.get("pull_count", "0")),
                        format_date(r.get("updated_at", "")),
                        r.get("short_description", "") or ""
                    )
                
        except httpx.RequestError as e:
            status.update(f"Request error: {e}")
        except httpx.HTTPStatusError as e:
            status.update(f"HTTP error: {e.response.status_code}")
        finally:
            self._loading_page = False


if __name__ == "__main__":
    app = DockerDorkerApp()
    app.run()
