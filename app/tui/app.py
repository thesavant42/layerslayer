"""
dockerDorkerUI

A basic UI structure with:
- Header (docked top)
- Left Panel with search input and tabbed results/FS simulator
- Right Panel with repo overview and tag selection
- Footer (docked bottom)
"""

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.content import Content
from textual.widgets import (
    Header, Footer, Static, Input, DataTable,
    TabbedContent, TabPane, Select, Button
)
from textual import work
import httpx
import io
import re
import sys
from pathlib import Path
from rich.text import Text
from urllib.parse import quote

# Add project root to path for imports when running directly
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import parsing functions for raw Docker Hub format
from app.modules.search.search_dockerhub import get_results, format_date

# Import from refactored submodules
from app.tui.utils import format_config, is_binary_content, parse_slug
from app.tui.modals import FileActionModal, TextViewerModal, SaveFileModal
from app.tui.widgets import SearchPanel, RepoPanel, FSSimulator, HistoryPanel, parse_fslog_line


class LeftPanel(Static):
    """Left panel widget with tabbed content for search results and FS simulator."""
    
    def compose(self) -> ComposeResult:
        with TabbedContent(id="left-tabs"):
            with TabPane("Search Results", id="search-results-tab"):
                yield SearchPanel(id="search-panel")
            with TabPane("FS Simulator", id="fs-simulator-tab"):
                yield FSSimulator(id="fs-simulator")


class RightPanel(Static):
    """Right panel widget with tabbed content for image build details."""
    
    def compose(self) -> ComposeResult:
        with TabbedContent(id="right-tabs"):
            with TabPane("Repo Overview", id="repo-overview"):
                yield RepoPanel(id="repo-panel")
            with TabPane("History", id="history-tab"):
                yield HistoryPanel(id="history-panel")


class DockerDorkerApp(App):
    """dockerDorker - A Textual app with a basic UI layout."""

    CSS_PATH = [
        "styles.tcss",
        "modals/styles.tcss",
        "widgets/search_panel/styles.tcss",
        "widgets/repo_panel/styles.tcss",
        "widgets/fs_simulator/styles.tcss",
        "widgets/history_panel/styles.tcss",
    ]
    TITLE = "dockerDorker"
    SUB_TITLE = "by @thesavant42"

    # Pagination state
    current_query: str = ""
    current_page: int = 1
    total_results: int = 0
    _loading_page: bool = False

    # Tag enumeration state
    selected_namespace: str = ""
    selected_repo: str = ""
    selected_tag: str = ""
    available_tags: list = []

    # FS Simulator state
    fs_image: str = ""
    fs_path: str = "/"
    fs_layer: int | None = None
    _loading_fs: bool = False

    # History state
    history_query: str = ""
    history_page: int = 1
    _loading_history: bool = False

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header(show_clock=True)
        with Horizontal(id="main-content"):
            yield LeftPanel(id="left-panel")
            yield RightPanel(id="right-panel")
        yield Footer()

    def on_mount(self) -> None:
        """Set theme and configure tables when app mounts."""
        self.theme = "flexoki"
        
        # Setup search results table
        search_panel = self.query_one("#search-panel", SearchPanel)
        search_panel.setup_table()
        
        # Setup config table
        repo_panel = self.query_one("#repo-panel", RepoPanel)
        repo_panel.setup_table()
        
        # Setup FS table
        fs_simulator = self.query_one("#fs-simulator", FSSimulator)
        fs_simulator.setup_table()
        
        # Setup history table
        history_panel = self.query_one("#history-panel", HistoryPanel)
        history_panel.setup_table()
        
        # Load initial history
        self.fetch_history_page(page=1)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input submission."""
        query = event.value.strip()
        
        if event.input.id == "search-input":
            if not query:
                return
            self.current_query = query
            self.current_page = 1
            status = self.query_one("#search-status", Static)
            status.update(f"Searching for: {query}...")
            self.fetch_page(query, page=1, clear=True)
        elif event.input.id == "history-filter-input":
            self.history_query = query
            self.history_page = 1
            self.fetch_history_page(query=query, page=1, clear=True)

    def on_key(self, event) -> None:
        """Handle key events for pagination at boundaries."""
        if self._loading_page:
            return
        
        table = self.query_one("#results-table", DataTable)
        if not table.has_focus:
            return
        
        if event.key == "up" and table.cursor_row == 0 and self.current_page > 1:
            self.fetch_page(self.current_query, self.current_page - 1, clear=True)
            event.prevent_default()
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
                    params={"q": query, "page": page, "sort": "updated_at", "order": "desc"}
                )
                response.raise_for_status()
                
                data = response.json()
                results, total = get_results(data)
                
                self.current_page = page
                self.total_results = total
                status.update("")
                self.update_pagination_display()
                
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

    def update_pagination_display(self) -> None:
        """Update pagination status text."""
        status = self.query_one("#pagination-status", Static)
        if self.total_results:
            total_pages = max(1, -(-self.total_results // 30))
            status.update(f"Page {self.current_page} of {total_pages} ({self.total_results} Results)")
        else:
            status.update("Page 1 of -- (-- Results)")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle pagination button presses."""
        button_id = event.button.id
        
        # Search pagination buttons
        if button_id in ("btn-first", "btn-prev", "btn-next", "btn-last"):
            if not self.current_query or self._loading_page:
                return
            
            total_pages = max(1, -(-self.total_results // 30))
            
            if button_id == "btn-first":
                target = 1
            elif button_id == "btn-prev":
                target = max(1, self.current_page - 1)
            elif button_id == "btn-next":
                target = min(total_pages, self.current_page + 1)
            elif button_id == "btn-last":
                target = total_pages
            else:
                return
            
            if target != self.current_page:
                self.fetch_page(self.current_query, target, clear=True)
        
        # History pagination buttons
        elif button_id in ("btn-history-first", "btn-history-prev", "btn-history-next", "btn-history-last"):
            if self._loading_history:
                return
            
            if button_id == "btn-history-first":
                self.fetch_history_page(query=self.history_query, page=1, clear=True)
            elif button_id == "btn-history-prev":
                if self.history_page > 1:
                    self.fetch_history_page(query=self.history_query, page=self.history_page - 1, clear=True)
            elif button_id == "btn-history-next":
                self.fetch_history_page(query=self.history_query, page=self.history_page + 1, clear=True)
            elif button_id == "btn-history-last":
                self.fetch_history_page(query=self.history_query, page=self.history_page + 1, clear=True)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection for results-table, config-table, fs-table, and history-table."""
        table = event.data_table
        cursor_row = event.cursor_row
        
        if cursor_row < 0 or cursor_row >= table.row_count:
            return
        
        row_data = table.get_row_at(cursor_row)
        if not row_data:
            return
        
        if table.id == "results-table":
            self._handle_results_row_selection(row_data)
        elif table.id == "config-table":
            self._handle_config_row_selection(row_data)
        elif table.id == "fs-table":
            self._handle_fs_row_selection(row_data)
        elif table.id == "history-table":
            self._handle_history_row_selection(row_data)

    def _handle_results_row_selection(self, row_data: tuple) -> None:
        """Handle selection in results-table to trigger tag enumeration."""
        slug = str(row_data[0])
        if not slug:
            return
        
        namespace, repo = parse_slug(slug)
        self.selected_namespace = namespace
        self.selected_repo = repo
        
        repo_info = self.query_one("#repo-info", Static)
        repo_info.update(f"Loading tags for {namespace}/{repo}...")
        
        config_table = self.query_one("#config-table", DataTable)
        config_table.clear(columns=True)
        
        self.enumerate_tags(namespace, repo)

    def _handle_config_row_selection(self, row_data: tuple) -> None:
        """Handle selection in config-table to trigger FS Simulator."""
        cell_value = row_data[0]
        if hasattr(cell_value, 'plain'):
            row_text = cell_value.plain
        else:
            row_text = str(cell_value)
        
        if row_text.startswith("rootfs.type:"):
            self.fs_layer = None
            self._trigger_fs_simulator()
        elif row_text.startswith("rootfs.diff_ids["):
            match = re.match(r'rootfs\.diff_ids\[(\d+)\]:', row_text)
            if match:
                self.fs_layer = int(match.group(1))
                self._trigger_fs_simulator()

    def _trigger_fs_simulator(self) -> None:
        """Start the FS Simulator flow."""
        if not self.selected_namespace or not self.selected_repo or not self.selected_tag:
            fs_status = self.query_one("#fs-status", Static)
            fs_status.update("Error: No image selected. Select a tag first.")
            return
        
        self.fs_image = f"{self.selected_namespace}/{self.selected_repo}:{self.selected_tag}"
        self.fs_path = "/"
        
        fs_status = self.query_one("#fs-status", Static)
        layer_desc = f"layer {self.fs_layer}" if self.fs_layer is not None else "all layers (merged)"
        fs_status.update(f"Loading {self.fs_image} - {layer_desc}...")
        
        left_tabs = self.query_one("#left-tabs", TabbedContent)
        left_tabs.active = "fs-simulator-tab"
        
        self.check_and_load_fslog()

    def _handle_fs_row_selection(self, row_data: tuple) -> None:
        """Handle selection in fs-table for directory navigation and file actions."""
        if self._loading_fs:
            return
        
        name = str(row_data[3])
        layer_col = str(row_data[4]) if len(row_data) > 4 else ""
        
        if name == "..":
            if self.fs_path != "/":
                self.fs_path = "/".join(self.fs_path.rstrip("/").split("/")[:-1]) or "/"
                self.load_fslog()
            return
        
        if name.endswith("/"):
            dir_name = name.rstrip("/")
            if self.fs_path == "/":
                self.fs_path = f"/{dir_name}"
            else:
                self.fs_path = f"{self.fs_path}/{dir_name}"
            self.load_fslog()
            return
        
        actual_name = name
        if " -> " in name:
            actual_name = name.split(" -> ")[0].strip()
        
        effective_layer: int | None = None
        
        if layer_col and layer_col.startswith("L"):
            try:
                effective_layer = int(layer_col[1:])
            except ValueError:
                pass
        
        if effective_layer is None and self.fs_layer is not None:
            effective_layer = self.fs_layer
        
        if effective_layer is None:
            fs_status = self.query_one("#fs-status", Static)
            fs_status.update("Error: Cannot determine layer. Select a specific layer first.")
            self.notify("Select a specific layer to carve files", severity="error")
            return
        
        if self.fs_path == "/":
            full_path = f"/{actual_name}"
        else:
            full_path = f"{self.fs_path}/{actual_name}"
        
        self.push_screen(
            FileActionModal(actual_name, full_path, effective_layer),
            callback=self._on_file_action_chosen
        )

    def _on_file_action_chosen(self, result: dict | None) -> None:
        """Handle modal result for file action."""
        if result is None:
            return
        
        action = result.get("action")
        file_path = result.get("path")
        layer = result.get("layer")
        filename = result.get("filename")
        
        if action == "view":
            self.carve_file_as_text(file_path, layer, filename)
        elif action == "save":
            if "." in filename:
                name_parts = filename.rsplit(".", 1)
                default_filename = f"{name_parts[0]}_L{layer}.{name_parts[1]}"
            else:
                default_filename = f"{filename}_L{layer}"
            
            self.push_screen(
                SaveFileModal(default_filename, file_path, layer),
                callback=self._on_save_filename_chosen
            )

    def _on_save_filename_chosen(self, result: dict | None) -> None:
        """Handle save filename modal result."""
        if result is None:
            return
        
        filename = result.get("filename")
        file_path = result.get("path")
        layer = result.get("layer")
        
        self.carve_file_download(file_path, layer, filename)

    @work(exclusive=True, group="carve")
    async def carve_file_as_text(self, file_path: str, layer: int, filename: str) -> None:
        """Fetch file content and display as text."""
        fs_status = self.query_one("#fs-status", Static)
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                fs_status.update(f"Fetching {file_path} from layer {layer}...")
                
                response = await client.get(
                    "http://127.0.0.1:8000/carve",
                    params={"image": self.fs_image, "path": file_path, "layer": layer, "as_text": True}
                )
                response.raise_for_status()
                
                content = response.text
                
                if is_binary_content(content):
                    fs_status.update(f"Cannot display binary file: {file_path}")
                    self.notify(
                        f"'{filename}' appears to be a binary file. Use Save/Download instead.",
                        severity="warning",
                        title="Binary File Detected"
                    )
                    return
                
                title = f"{filename} (Layer {layer})"
                self.push_screen(TextViewerModal(title, content))
                fs_status.update(f"Viewing: {file_path}")
                
        except httpx.RequestError as e:
            fs_status.update(f"Request error: {e}")
            self.notify(f"Failed to fetch file: {e}", severity="error")
        except httpx.HTTPStatusError as e:
            fs_status.update(f"HTTP error: {e.response.status_code}")
            self.notify(f"Failed to fetch file: HTTP {e.response.status_code}", severity="error")

    @work(exclusive=True, group="carve")
    async def carve_file_download(self, file_path: str, layer: int, filename: str) -> None:
        """Download file and save to Downloads folder."""
        fs_status = self.query_one("#fs-status", Static)
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                fs_status.update(f"Downloading {file_path} from layer {layer}...")
                
                response = await client.get(
                    "http://127.0.0.1:8000/carve",
                    params={"image": self.fs_image, "path": file_path, "layer": layer}
                )
                response.raise_for_status()
                
                content_bytes = response.content
                content_length = len(content_bytes)
                
                # Write directly to app/loot folder
                loot_dir = (project_root / "app" / "loot").resolve()
                loot_dir.mkdir(parents=True, exist_ok=True)
                save_path = loot_dir / filename
                save_path.write_bytes(content_bytes)
                
                fs_status.update(f"Saved: {save_path} ({content_length} bytes)")
                self.notify(f"Saved to {save_path} ({content_length} bytes)", title="Download Complete")
                
        except httpx.RequestError as e:
            fs_status.update(f"Request error: {e}")
            self.notify(f"Failed to download file: {e}", severity="error")
        except httpx.HTTPStatusError as e:
            fs_status.update(f"HTTP error: {e.response.status_code}")
            self.notify(f"Failed to download file: HTTP {e.response.status_code}", severity="error")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle tag selection - fetch config manifest."""
        if event.select.id != "tag-select":
            return
        
        if event.value is None or event.value == Select.BLANK:
            return
        
        tag = str(event.value)
        self.selected_tag = tag
        
        repo_info = self.query_one("#repo-info", Static)
        repo_info.update(f"Loading config for tag: {tag}...")
        
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
                    params={"page": 1, "page_size": 30, "ordering": "last_updated"}
                )
                response.raise_for_status()
                
                data = response.json()
                results = data.get("results", [])
                count = data.get("count", 0)
                
                self.available_tags = results
                options = [(tag["name"], tag["name"]) for tag in results if "name" in tag]
                tag_select.set_options(options)
                
                repo_info.update(f"{namespace}/{repo} - {count} tags ({len(options)} shown)")
                
        except httpx.RequestError as e:
            repo_info.update(f"Request error: {e}")
        except httpx.HTTPStatusError as e:
            repo_info.update(f"HTTP error: {e.response.status_code}")

    @work(exclusive=True, group="config")
    async def fetch_tag_config(self, namespace: str, repo: str, tag: str) -> None:
        """Fetch config manifest for tag and populate DataTable."""
        config_table = self.query_one("#config-table", DataTable)
        repo_info = self.query_one("#repo-info", Static)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://127.0.0.1:8000/repositories/{namespace}/{repo}/tags/{tag}/config",
                    params={"force_refresh": False}
                )
                response.raise_for_status()
                
                config = response.json()
                
                config_table.clear(columns=True)
                config_table.show_header = False
                config_table.add_column("DATA", width=180)
                
                rows = format_config(config)
                HIGHLIGHT_FIELDS = {"WorkingDir", "rootfs.type"}
                for field, value in rows:
                    if field:
                        if field in HIGHLIGHT_FIELDS:
                            config_table.add_row(Content.from_markup(f"[bold $accent]{field}: {value}[/]"))
                        else:
                            config_table.add_row(f"{field}: {value}")
                    else:
                        config_table.add_row(value)
                
                repo_info.update(f"{namespace}/{repo}:{tag} - {len(rows)} fields")
                
        except httpx.RequestError as e:
            repo_info.update(f"Request error: {e}")
        except httpx.HTTPStatusError as e:
            repo_info.update(f"HTTP error: {e.response.status_code}")

    @work(exclusive=True, group="fslog")
    async def check_and_load_fslog(self) -> None:
        """Check peek status and peek if needed, then load fslog."""
        self._loading_fs = True
        fs_status = self.query_one("#fs-status", Static)
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                fs_status.update(f"Checking peek status for {self.fs_image}...")
                
                status_response = await client.get(
                    "http://127.0.0.1:8000/peek",
                    params={"image": self.fs_image, "status_only": True}
                )
                status_response.raise_for_status()
                status_data = status_response.json()
                
                layers_to_peek = []
                
                if self.fs_layer is not None:
                    layers = status_data.get("layers", [])
                    for layer in layers:
                        if layer.get("idx") == self.fs_layer and not layer.get("peeked", False):
                            layers_to_peek.append(self.fs_layer)
                            break
                else:
                    layers = status_data.get("layers", [])
                    for layer in layers:
                        if not layer.get("peeked", False):
                            layers_to_peek.append(layer.get("idx"))
                
                if layers_to_peek:
                    for layer_idx in layers_to_peek:
                        fs_status.update(f"Peeking layer {layer_idx} of {self.fs_image}...")
                        
                        peek_response = await client.get(
                            "http://127.0.0.1:8000/peek",
                            params={
                                "image": self.fs_image,
                                "layer": str(layer_idx),
                                "status_only": False,
                                "hide_build": True
                            },
                            timeout=120.0
                        )
                        peek_response.raise_for_status()
                
                await self._do_load_fslog()
                
        except httpx.RequestError as e:
            fs_status.update(f"Request error: {e}")
        except httpx.HTTPStatusError as e:
            fs_status.update(f"HTTP error: {e.response.status_code}")
        finally:
            self._loading_fs = False

    @work(exclusive=True, group="fslog")
    async def load_fslog(self) -> None:
        """Load fslog for current path (called during directory navigation)."""
        self._loading_fs = True
        try:
            await self._do_load_fslog()
        finally:
            self._loading_fs = False

    async def _do_load_fslog(self) -> None:
        """Internal method to load fslog data and populate table."""
        fs_status = self.query_one("#fs-status", Static)
        fs_breadcrumb = self.query_one("#fs-breadcrumb", Static)
        fs_table = self.query_one("#fs-table", DataTable)
        
        layer_desc = f"layer {self.fs_layer}" if self.fs_layer is not None else "all layers"
        fs_status.update(f"Loading {self.fs_path} from {self.fs_image} ({layer_desc})...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {"image": self.fs_image, "path": self.fs_path}
                if self.fs_layer is not None:
                    params["layer"] = self.fs_layer
                
                response = await client.get("http://127.0.0.1:8000/fslog", params=params)
                response.raise_for_status()
                
                content = response.text
                lines = content.strip().split("\n") if content.strip() else []
                
                fs_table.clear()
                
                if self.fs_path != "/":
                    fs_table.add_row("", "", "", "..", "")
                
                for line in lines:
                    entry = parse_fslog_line(line)
                    if entry:
                        fs_table.add_row(
                            entry["mode"],
                            entry["size"],
                            entry["date"],
                            entry["name"],
                            entry.get("layer", "")
                        )
                
                fs_breadcrumb.update(f"Path: {self.fs_path}")
                entry_count = len(lines)
                fs_status.update(f"{self.fs_image} - {self.fs_path} - {entry_count} entries ({layer_desc})")
                
        except httpx.RequestError as e:
            fs_status.update(f"Request error: {e}")
        except httpx.HTTPStatusError as e:
            fs_status.update(f"HTTP error: {e.response.status_code}")


    @work(exclusive=True, group="history")
    async def fetch_history_page(self, query: str = "", page: int = 1, clear: bool = False) -> None:
        """Fetch history page from API."""
        self._loading_history = True
        status = self.query_one("#history-status", Static)
        table = self.query_one("#history-table", DataTable)
        
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "page": page,
                    "page_size": 30,
                    "sortby": "scraped_at",
                    "order": "desc"
                }
                if query:
                    params["q"] = query
                
                response = await client.get(
                    "http://127.0.0.1:8000/history",
                    params=params
                )
                response.raise_for_status()
                
                # Parse plain text response
                lines = response.text.strip().split("\n")
                
                self.history_page = page
                status.update("")
                self.update_history_pagination()
                
                if clear:
                    table.clear()
                
                # Skip header and separator lines (first 2 lines)
                for line in lines[2:]:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 6:
                        table.add_row(
                            parts[0],  # scraped_at
                            parts[1],  # owner
                            parts[2],  # repo
                            parts[3],  # tag
                            parts[4],  # idx
                            parts[5],  # layer_size
                        )
        except httpx.RequestError as e:
            status.update(f"Request error: {e}")
        except httpx.HTTPStatusError as e:
            status.update(f"HTTP error: {e.response.status_code}")
        finally:
            self._loading_history = False

    def update_history_pagination(self) -> None:
        """Update history pagination status."""
        status = self.query_one("#history-pagination-status", Static)
        table = self.query_one("#history-table", DataTable)
        row_count = table.row_count
        status.update(f"Page {self.history_page} ({row_count} results)")

    def _handle_history_row_selection(self, row_data: tuple) -> None:
        """Handle selection in history-table to load layer into FS Simulator."""
        if len(row_data) < 5:
            return
        
        owner = str(row_data[1]).strip()
        repo = str(row_data[2]).strip()
        tag = str(row_data[3]).strip()
        idx_str = str(row_data[4]).strip()
        
        try:
            layer_idx = int(idx_str)
        except ValueError:
            return
        
        # Set state for FS Simulator
        self.selected_namespace = owner
        self.selected_repo = repo
        self.selected_tag = tag
        self.fs_image = f"{owner}/{repo}:{tag}"
        self.fs_path = "/"
        self.fs_layer = layer_idx
        
        # Update status and switch to FS Simulator tab
        fs_status = self.query_one("#fs-status", Static)
        fs_status.update(f"Loading {self.fs_image} layer {layer_idx} from history...")
        
        left_tabs = self.query_one("#left-tabs", TabbedContent)
        left_tabs.active = "fs-simulator-tab"
        
        # Load the layer
        self.check_and_load_fslog()


if __name__ == "__main__":
    app = DockerDorkerApp()
    app.run()
