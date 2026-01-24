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
from textual.widgets import Header, Footer, Static, Input
from textual import work
import httpx


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

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header(show_clock=True)
        yield TopPanel(id="top-panel")
        with Horizontal(id="main-content"):
            yield LeftPanel("Search Results go Here", id="left-panel")
            yield RightPanel("Right Panel", id="right-panel")
        yield Footer()

    def on_mount(self) -> None:
        """Set the Dracula theme when the app mounts."""
        self.theme = "dracula"

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input submission."""
        query = event.value.strip()
        if not query:
            return
        
        # Update status and trigger the worker
        status = self.query_one("#search-status", Static)
        status.update(f"Searching for: {query}...")
        self.search_docker_hub(query)

    @work(exclusive=True)
    async def search_docker_hub(self, query: str) -> None:
        """Worker to perform the search API call."""
        status = self.query_one("#search-status", Static)
        left_panel = self.query_one("#left-panel", LeftPanel)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://127.0.0.1:8000/search.data",
                    params={
                        "q": query,
                        "page": 1,
                        "sortby": "updated_at",
                        "order": "desc"
                    }
                )
                response.raise_for_status()
                
                # API returns plain text, not JSON
                text_data = response.text
                
                # Clear status since results now display in left panel
                status.update("")
                
                # Display full results in left panel
                left_panel.update(text_data)
                
        except httpx.RequestError as e:
            status.update(f"Request error: {e}")
            left_panel.update(f"Request error: {e}")
        except httpx.HTTPStatusError as e:
            status.update(f"HTTP error: {e.response.status_code}")
            left_panel.update(f"HTTP error: {e.response.status_code}")


if __name__ == "__main__":
    app = DockerDorkerApp()
    app.run()
