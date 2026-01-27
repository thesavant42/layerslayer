"""
Save File Modal - Choose filename before downloading a file.
"""

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Input


class SaveFileModal(ModalScreen):
    """Modal to choose save filename before downloading."""
    
    BINDINGS = [("escape", "cancel", "Cancel")]
    
    def __init__(self, default_filename: str, file_path: str, layer_idx: int):
        super().__init__()
        self.default_filename = default_filename
        self.file_path = file_path
        self.layer_idx = layer_idx
    
    def compose(self) -> ComposeResult:
        with Vertical(id="save-file-dialog"):
            yield Label("Save File As", id="save-file-title")
            yield Label(f"Source: {self.file_path} (Layer {self.layer_idx})", id="save-file-source")
            yield Input(value=self.default_filename, id="save-filename-input", placeholder="Enter filename...")
            with Horizontal(id="save-file-buttons"):
                yield Button("Save", id="btn-confirm-save", variant="primary")
                yield Button("Cancel", id="btn-cancel-save", variant="warning")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm-save":
            filename_input = self.query_one("#save-filename-input", Input)
            filename = filename_input.value.strip()
            if filename:
                self.dismiss(result={
                    "filename": filename,
                    "path": self.file_path,
                    "layer": self.layer_idx
                })
            else:
                self.notify("Please enter a filename", severity="warning")
        else:
            self.dismiss(result=None)
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in the filename input."""
        if event.input.id == "save-filename-input":
            filename = event.value.strip()
            if filename:
                self.dismiss(result={
                    "filename": filename,
                    "path": self.file_path,
                    "layer": self.layer_idx
                })
    
    def action_cancel(self) -> None:
        self.dismiss(result=None)
