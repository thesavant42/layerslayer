"""
Text Viewer Modal - Display file content as scrollable text.
"""

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static
from rich.text import Text


class TextViewerModal(ModalScreen):
    """Modal to display file content as text."""
    
    BINDINGS = [("escape", "close", "Close"), ("q", "close", "Close")]
    
    def __init__(self, title: str, content: str):
        super().__init__()
        self.title_text = title
        self.content_text = content
    
    def compose(self) -> ComposeResult:
        with Vertical(id="text-viewer-dialog"):
            yield Label(self.title_text, id="text-viewer-title")
            with VerticalScroll(id="text-viewer-scroll"):
                # Wrap content in Text() to prevent markup parsing crashes
                yield Static(Text(self.content_text), id="text-viewer-content")
            yield Button("Close", id="btn-close-viewer")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-viewer":
            self.dismiss()
    
    def action_close(self) -> None:
        self.dismiss()
