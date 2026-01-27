"""
File Action Modal - Choose between viewing as text or saving/downloading a file.
"""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class FileActionModal(ModalScreen):
    """Modal to choose file action: View as Text or Save/Download."""
    
    BINDINGS = [("escape", "cancel", "Cancel")]
    
    def __init__(self, filename: str, full_path: str, layer_idx: int):
        super().__init__()
        self.filename = filename
        self.full_path = full_path
        self.layer_idx = layer_idx
    
    def compose(self) -> ComposeResult:
        with Vertical(id="file-action-dialog"):
            yield Label(f"File: {self.filename}", id="file-action-title")
            yield Label(f"Path: {self.full_path}", id="file-action-path")
            yield Label(f"Layer: {self.layer_idx}", id="file-action-layer")
            yield Button("View as Text", id="btn-view-text", variant="primary")
            yield Button("Save/Download", id="btn-save-file", variant="default")
            yield Button("Cancel", id="btn-cancel", variant="warning")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-view-text":
            self.dismiss(result={"action": "view", "path": self.full_path, "layer": self.layer_idx, "filename": self.filename})
        elif event.button.id == "btn-save-file":
            self.dismiss(result={"action": "save", "path": self.full_path, "layer": self.layer_idx, "filename": self.filename})
        else:
            self.dismiss(result=None)
    
    def action_cancel(self) -> None:
        self.dismiss(result=None)
