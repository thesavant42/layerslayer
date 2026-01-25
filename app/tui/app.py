"""
dockerDorkerUI

A basic UI structure with:
- Header (docked top)
- Top Panel (1/3) with search input
- Left/Right Panels (50/50 split, 2/3 height)
- Footer (docked bottom)
"""

from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import (
    Header, Footer, Static, Input, DataTable,
    TabbedContent, TabPane, Select
)
from textual.binding import Binding
from textual import work
import httpx
import json
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
    """Right panel widget with tabbed content for repo details."""
    
    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Repo Overview", id="repo-overview"):
                yield Static("Select a repository to view tags", id="repo-info")
                yield Select([], id="tag-select", prompt="Select a tag...")
                with VerticalScroll(id="config-scroll"):
                    yield Static("", id="config-display")


def parse_slug(slug: str) -> tuple[str, str]:
    """Extract namespace and repo from slug.
    
    Args:
        slug: Repository slug like 'library/nginx' or 'username/reponame'
        
    Returns:
        Tuple of (namespace, repo)
    """
    parts = slug.split("/", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    # Handle single-part slugs - assume 'library' namespace
    return "library", parts[0]


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
    
    # Tag enumeration state
    selected_namespace: str = ""
    selected_repo: str = ""
    available_tags: list = []

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header(show_clock=True)
        yield TopPanel(id="top-panel")
        with Horizontal(id="main-content"):
            yield DataTable(id="results-table", cursor_type="row")
            yield RightPanel(id="right-panel")
        yield Footer()

    def on_mount(self) -> None:
        """Set the Dracula theme when the app mounts."""
        self.theme = "dracula"
        table = self.query_one("#results-table", DataTable)
        table.add_column("SLUG", width=50)
        table.add_column("FAV", width=4)
        table.add_column("PULLS", width=6)
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

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection - trigger tag enumeration."""
        table = event.data_table
        cursor_row = event.cursor_row
        
        # Get the row data using cursor position
        if cursor_row < 0 or cursor_row >= table.row_count:
            return
        
        # Get row data - returns tuple of cell values in column order
        row_data = table.get_row_at(cursor_row)
        if not row_data:
            return
        
        # First column (index 0) is SLUG
        slug = str(row_data[0])
        if not slug:
            return
        
        # Parse namespace and repo from slug
        namespace, repo = parse_slug(slug)
        self.selected_namespace = namespace
        self.selected_repo = repo
        
        # Update repo info display
        repo_info = self.query_one("#repo-info", Static)
        repo_info.update(f"Loading tags for {namespace}/{repo}...")
        
        # Clear previous config display
        config_display = self.query_one("#config-display", Static)
        config_display.update("")
        
        # Trigger tag enumeration
        self.enumerate_tags(namespace, repo)

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle tag selection - fetch config manifest."""
        if event.select.id != "tag-select":
            return
        
        if event.value is None or event.value == Select.BLANK:
            return
        
        tag = str(event.value)
        
        # Update display to show loading
        config_display = self.query_one("#config-display", Static)
        config_display.update(f"Loading config for tag: {tag}...")
        
        # Fetch the config manifest
        self.fetch_tag_config(self.selected_namespace, self.selected_repo, tag)

    @work(exclusive=True, group="tags")
    async def enumerate_tags(self, namespace: str, repo: str) -> None:
        """Fetch tags for repository."""
        repo_info = self.query_one("#repo-info", Static)
        tag_select = self.query_one("#tag-select", Select)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://127.0.0.1:8000/repositories/{namespace}/{repo}/tags",
                    params={
                        "page": 1,
                        "page_size": 30,
                        "ordering": "last_updated"
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                results = data.get("results", [])
                count = data.get("count", 0)
                
                # Store available tags
                self.available_tags = results
                
                # Build options for Select widget: list of (display_text, value) tuples
                options = [(tag["name"], tag["name"]) for tag in results if "name" in tag]
                
                # Update Select widget with new options
                tag_select.set_options(options)
                
                # Update repo info with tag count
                repo_info.update(f"{namespace}/{repo} - {count} tags ({len(options)} shown)")
                
        except httpx.RequestError as e:
            repo_info.update(f"Request error: {e}")
        except httpx.HTTPStatusError as e:
            repo_info.update(f"HTTP error: {e.response.status_code}")

    @work(exclusive=True, group="config")
    async def fetch_tag_config(self, namespace: str, repo: str, tag: str) -> None:
        """Fetch config manifest for tag."""
        config_display = self.query_one("#config-display", Static)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://127.0.0.1:8000/repositories/{namespace}/{repo}/tags/{tag}/config",
                    params={"force_refresh": False}
                )
                response.raise_for_status()
                
                config = response.json()
                
                # Format JSON with indentation for readability
                formatted_json = json.dumps(config, indent=2)
                
                # Update config display
                config_display.update(formatted_json)
                
        except httpx.RequestError as e:
            config_display.update(f"Request error: {e}")
        except httpx.HTTPStatusError as e:
            config_display.update(f"HTTP error: {e.response.status_code}")


if __name__ == "__main__":
    app = DockerDorkerApp()
    app.run()
