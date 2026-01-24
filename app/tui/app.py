"""
dockerDorkerUI

A basic UI structure with:
- Header (docked top)
- Top Panel (1/3)
- Left/Right Panels (50/50 split, 2/3 height)
- Footer (docked bottom)
"""

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Header, Footer, Static


class TopPanel(Static):
    """Top panel  widget."""
    pass


class LeftPanel(Static):
    """Left panel  widget (50% width)."""
    pass


class RightPanel(Static):
    """Right panel  widget (50% width)."""
    pass


class DockerDorkerApp(App):
    """dockerDorker - A Textual app with a basic UI layout."""

    CSS_PATH = "styles.tcss"
    TITLE = "dockerDorker"
    SUB_TITLE = "by @thesavant42"

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header(show_clock=True)
        yield TopPanel("dockerDorker", id="top-panel")
        with Horizontal(id="main-content"):
            yield LeftPanel("Left Panel", id="left-panel")
            yield RightPanel("Main Panel", id="right-panel")
        yield Footer()

    def on_mount(self) -> None:
        """Set the Dracula theme when the app mounts."""
        self.theme = "dracula"


if __name__ == "__main__":
    app = DockerDorkerApp()
    app.run()
