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
    TabbedContent, TabPane, Select, Button
)
from textual.binding import Binding
from textual import work
import httpx
import json
import sys
import re
from pathlib import Path
from rich.text import Text
from urllib.parse import quote

# Add project root to path for imports when running directly
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import parsing functions for raw Docker Hub format
from app.modules.search.search_dockerhub import get_results, format_date


def format_history_date(iso_date: str) -> str:
    """Convert ISO date to MM-DD-YYYY format.
    
    Args:
        iso_date: ISO 8601 date string like '2025-01-27T04:14:00.804659581Z'
        
    Returns:
        Formatted date string like '01-27-2025'
    """
    if not iso_date:
        return ""
    try:
        # Parse ISO format and reformat
        date_part = iso_date.split("T")[0]  # '2025-01-27'
        parts = date_part.split("-")  # ['2025', '01', '27']
        if len(parts) == 3:
            return f"{parts[1]}-{parts[2]}-{parts[0]}"  # MM-DD-YYYY
    except Exception:
        pass
    return iso_date


def flatten_nested(obj: dict | list, prefix: str = "") -> list[tuple[str, str]]:
    """Flatten nested dict/list into (field, value) tuples with dot notation."""
    rows = []
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            field = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                rows.extend(flatten_nested(value, field))
            elif isinstance(value, list):
                if len(value) == 0:
                    rows.append((field, "(empty list)"))
                else:
                    for i, item in enumerate(value):
                        item_field = f"{field}[{i}]"
                        if isinstance(item, dict):
                            rows.extend(flatten_nested(item, item_field))
                        else:
                            rows.append((item_field, str(item)))
            elif value is None:
                rows.append((field, "(null)"))
            else:
                rows.append((field, str(value)))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            item_field = f"{prefix}[{i}]" if prefix else f"[{i}]"
            if isinstance(item, dict):
                rows.extend(flatten_nested(item, item_field))
            else:
                rows.append((item_field, str(item)))
    
    return rows


def format_config(config: dict) -> list[tuple[str, str]]:
    """Format OCI config JSON for display per tags-TASK.md requirements.
    
    Groups data in order:
    1. architecture, os (top-level)
    2. config.* values
    3. history entries combined: MM-DD-YYYY - created_by (skip empty_layer)
    4. rootfs.type and rootfs.diff_ids
    
    Args:
        config: OCI config JSON dict
        
    Returns:
        List of (field_name, value_string) tuples
    """
    rows = []
    
    # 1. Architecture and OS at top
    if "architecture" in config:
        rows.append(("architecture", str(config["architecture"])))
    if "os" in config:
        rows.append(("os", str(config["os"])))
    
    # 2. Useful config.* values only (Env, Cmd, Entrypoint, Labels, WorkingDir, ExposedPorts)
    if "config" in config and isinstance(config["config"], dict):
        cfg = config["config"]
        
        # Env variables
        if "Env" in cfg and isinstance(cfg["Env"], list):
            for env_val in cfg["Env"]:
                rows.append(("", str(env_val)))
        
        # Cmd
        if "Cmd" in cfg and isinstance(cfg["Cmd"], list):
            rows.append(("Cmd", " ".join(cfg["Cmd"])))
        
        # Entrypoint
        if "Entrypoint" in cfg and isinstance(cfg["Entrypoint"], list):
            rows.append(("Entrypoint", " ".join(cfg["Entrypoint"])))
        
        # WorkingDir
        if "WorkingDir" in cfg and cfg["WorkingDir"]:
            rows.append(("WorkingDir", str(cfg["WorkingDir"])))
        
        # ExposedPorts
        if "ExposedPorts" in cfg and isinstance(cfg["ExposedPorts"], dict):
            for port in cfg["ExposedPorts"].keys():
                rows.append(("ExposedPort", str(port)))
        
        # Labels
        if "Labels" in cfg and isinstance(cfg["Labels"], dict):
            for key, val in cfg["Labels"].items():
                rows.append(("", f"{key}={val}"))
    
    # 3. History entries - combine date + created_by, skip empty_layer, no field label
    if "history" in config and isinstance(config["history"], list):
        for i, entry in enumerate(config["history"]):
            if not isinstance(entry, dict):
                continue
            
            created = entry.get("created", "")
            created_by = entry.get("created_by", "")
            
            # Format: MM-DD-YYYY - command (no field label, just the value)
            date_str = format_history_date(created)
            if date_str and created_by:
                rows.append(("", f"{date_str} - {created_by}"))
            elif created_by:
                rows.append(("", created_by))
            elif date_str:
                rows.append(("", date_str))
    
    # 4. rootfs.type and rootfs.diff_ids
    if "rootfs" in config and isinstance(config["rootfs"], dict):
        rootfs = config["rootfs"]
        if "type" in rootfs:
            rows.append(("rootfs.type", str(rootfs["type"])))
        if "diff_ids" in rootfs and isinstance(rootfs["diff_ids"], list):
            for i, diff_id in enumerate(rootfs["diff_ids"]):
                rows.append((f"rootfs.diff_ids[{i}]", str(diff_id)))
    
    return rows


class TopPanel(Static):
    """Top panel widget with search input."""
    # Do not set height to 0 Do not Collapse Do NOT delete!
    def compose(self) -> ComposeResult:
        yield Input(
            placeholder="Search Docker Hub...",
            id="search-input",
            type="text"
        )
        yield Static("", id="search-status")


class LeftPanel(Static):
    """Left panel widget with tabbed content for search results and FS simulator."""
    
    def compose(self) -> ComposeResult:
        with TabbedContent(id="left-tabs"):
            with TabPane("Search Results", id="search-results-tab"):
                yield Static("", id="left-spacer")
                yield DataTable(id="results-table", cursor_type="row")
                with Horizontal(id="pagination-bar"):
                    yield Button("<<", id="btn-first")
                    yield Button("<", id="btn-prev")
                    yield Button(">", id="btn-next")
                    yield Button(">>", id="btn-last")
                    yield Static("Page 1 of -- (-- Results)", id="pagination-status")
            with TabPane("FS Simulator", id="fs-simulator-tab"):
                yield Static("Select a layer from config to browse filesystem", id="fs-status")
                yield Static("Path: /", id="fs-breadcrumb")
                yield DataTable(id="fs-table", cursor_type="row")


class RightPanel(Static):
    """Right panel widget with tabbed content for image build details."""
    # TODO Fix these labels, this is TAGS overview, not REPOs
    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Repo Overview", id="repo-overview"):
                yield Static("Select a repository to view tags", id="repo-info")
                yield Select([], id="tag-select", prompt="Select a tag...")
                yield DataTable(id="config-table", cursor_type="row")


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
    selected_tag: str = ""
    available_tags: list = []
    
    # FS Simulator state
    fs_image: str = ""           # Current image: "namespace/repo:tag"
    fs_path: str = "/"           # Current directory path
    fs_layer: int | None = None  # None = merged view, int = single layer
    _loading_fs: bool = False    # Flag to prevent loading loops

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header(show_clock=True)
        yield TopPanel(id="top-panel")
        with Horizontal(id="main-content"):
            yield LeftPanel(id="left-panel")
            yield RightPanel(id="right-panel")
        yield Footer()

    def on_mount(self) -> None:
        """Set the Dracula theme when the app mounts."""
        self.theme = "dracula"
        table = self.query_one("#results-table", DataTable)
        table.zebra_stripes = True
        table.add_column("SLUG", width=50)
        table.add_column("FAV", width=4)
        table.add_column("PULLS", width=6)
        table.add_column("UPDATED", width=12)
        table.add_column("DESCRIPTION", width=80)
        
        config_table = self.query_one("#config-table", DataTable)
        config_table.zebra_stripes = True
        
        # Setup FS Simulator table
        fs_table = self.query_one("#fs-table", DataTable)
        fs_table.zebra_stripes = True
        fs_table.add_column("MODE", width=12)
        fs_table.add_column("SIZE", width=10)
        fs_table.add_column("DATE", width=18)
        fs_table.add_column("NAME", width=60)
        fs_table.add_column("LAYER", width=8)

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
        if not self.current_query or self._loading_page:
            return
        
        total_pages = max(1, -(-self.total_results // 30))
        
        if event.button.id == "btn-first":
            target = 1
        elif event.button.id == "btn-prev":
            target = max(1, self.current_page - 1)
        elif event.button.id == "btn-next":
            target = min(total_pages, self.current_page + 1)
        elif event.button.id == "btn-last":
            target = total_pages
        else:
            return
        
        if target != self.current_page:
            self.fetch_page(self.current_query, target, clear=True)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection for results-table, config-table, and fs-table."""
        table = event.data_table
        cursor_row = event.cursor_row
        
        # Get the row data using cursor position
        if cursor_row < 0 or cursor_row >= table.row_count:
            return
        
        row_data = table.get_row_at(cursor_row)
        if not row_data:
            return
        
        # Handle results-table - trigger tag enumeration
        if table.id == "results-table":
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
            
            # Clear previous config table
            config_table = self.query_one("#config-table", DataTable)
            config_table.clear(columns=True)
            
            # Trigger tag enumeration
            self.enumerate_tags(namespace, repo)
        
        # Handle config-table - trigger FS Simulator
        elif table.id == "config-table":
            self._handle_config_row_selection(row_data)
        
        # Handle fs-table - directory navigation
        elif table.id == "fs-table":
            self._handle_fs_row_selection(row_data)
    
    def _handle_config_row_selection(self, row_data: tuple) -> None:
        """Handle selection in config-table to trigger FS Simulator."""
        # Get the row text (single column DATA)
        cell_value = row_data[0]
        # Handle Text objects from rich
        if hasattr(cell_value, 'plain'):
            row_text = cell_value.plain
        else:
            row_text = str(cell_value)
        
        # Check if this is a rootfs.type or rootfs.diff_ids row
        if row_text.startswith("rootfs.type:"):
            # Merged view - all layers
            self.fs_layer = None
            self._trigger_fs_simulator()
        elif row_text.startswith("rootfs.diff_ids["):
            # Single layer view - extract layer index
            match = re.match(r'rootfs\.diff_ids\[(\d+)\]:', row_text)
            if match:
                layer_idx = int(match.group(1))
                self.fs_layer = layer_idx
                self._trigger_fs_simulator()
    
    def _trigger_fs_simulator(self) -> None:
        """Start the FS Simulator flow: check peek status, peek if needed, load fslog."""
        if not self.selected_namespace or not self.selected_repo or not self.selected_tag:
            fs_status = self.query_one("#fs-status", Static)
            fs_status.update("Error: No image selected. Select a tag first.")
            return
        
        # Build image reference
        self.fs_image = f"{self.selected_namespace}/{self.selected_repo}:{self.selected_tag}"
        self.fs_path = "/"
        
        # Update status
        fs_status = self.query_one("#fs-status", Static)
        layer_desc = f"layer {self.fs_layer}" if self.fs_layer is not None else "all layers (merged)"
        fs_status.update(f"Loading {self.fs_image} - {layer_desc}...")
        
        # Switch to FS Simulator tab
        left_tabs = self.query_one("#left-tabs", TabbedContent)
        left_tabs.active = "fs-simulator-tab"
        
        # Start the peek check and load workflow
        self.check_and_load_fslog()
    
    def _handle_fs_row_selection(self, row_data: tuple) -> None:
        """Handle selection in fs-table for directory navigation."""
        if self._loading_fs:
            return
        
        # NAME column is index 3
        name = str(row_data[3])
        
        # Handle .. navigation (parent directory)
        if name == "..":
            if self.fs_path != "/":
                # Go to parent directory
                self.fs_path = "/".join(self.fs_path.rstrip("/").split("/")[:-1]) or "/"
                self.load_fslog()
            return
        
        # Handle directory navigation (ends with /)
        if name.endswith("/"):
            dir_name = name.rstrip("/")
            # Build new path
            if self.fs_path == "/":
                self.fs_path = f"/{dir_name}"
            else:
                self.fs_path = f"{self.fs_path}/{dir_name}"
            self.load_fslog()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle tag selection - fetch config manifest."""
        if event.select.id != "tag-select":
            return
        
        if event.value is None or event.value == Select.BLANK:
            return
        
        tag = str(event.value)
        self.selected_tag = tag  # Store for FS Simulator use
        
        # Update repo info to show loading
        repo_info = self.query_one("#repo-info", Static)
        repo_info.update(f"Loading config for tag: {tag}...")
        
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
                
                # Clear and setup single column (no header)
                config_table.clear(columns=True)
                config_table.show_header = False
                config_table.add_column("DATA", width=180)
                
                # Format and add all rows with Text to prevent markup parsing
                rows = format_config(config)
                for field, value in rows:
                    # Combine field and value into single column
                    if field:
                        config_table.add_row(Text(f"{field}: {value}"))
                    else:
                        config_table.add_row(Text(value))
                
                # Update status
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
            image_encoded = quote(self.fs_image, safe='')
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Step 1: Check peek status
                fs_status.update(f"Checking peek status for {self.fs_image}...")
                
                status_response = await client.get(
                    "http://127.0.0.1:8000/peek",
                    params={
                        "image": self.fs_image,
                        "status_only": True
                    }
                )
                status_response.raise_for_status()
                status_data = status_response.json()
                
                # Determine which layers need peeking
                layers_to_peek = []
                
                if self.fs_layer is not None:
                    # Single layer mode - check if this specific layer is peeked
                    layers = status_data.get("layers", [])
                    for layer in layers:
                        if layer.get("idx") == self.fs_layer and not layer.get("peeked", False):
                            layers_to_peek.append(self.fs_layer)
                            break
                else:
                    # Merged mode - check all layers
                    layers = status_data.get("layers", [])
                    for layer in layers:
                        if not layer.get("peeked", False):
                            layers_to_peek.append(layer.get("idx"))
                
                # Step 2: Peek any unpeeked layers
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
                            timeout=120.0  # Layer peeking can take time
                        )
                        peek_response.raise_for_status()
                
                # Step 3: Load fslog
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
                # Build request params
                params = {
                    "image": self.fs_image,
                    "path": self.fs_path
                }
                if self.fs_layer is not None:
                    params["layer"] = self.fs_layer
                
                response = await client.get(
                    "http://127.0.0.1:8000/fslog",
                    params=params
                )
                response.raise_for_status()
                
                # Parse plain text response (ls -la style output)
                content = response.text
                lines = content.strip().split("\n") if content.strip() else []
                
                # Clear and repopulate table
                fs_table.clear()
                
                # Add .. breadcrumb row if not at root
                if self.fs_path != "/":
                    fs_table.add_row("", "", "", "..", "")
                
                # Parse and add each entry
                for line in lines:
                    entry = self._parse_fslog_line(line)
                    if entry:
                        fs_table.add_row(
                            entry["mode"],
                            entry["size"],
                            entry["date"],
                            entry["name"],
                            entry.get("layer", "")
                        )
                
                # Update breadcrumb and status
                fs_breadcrumb.update(f"Path: {self.fs_path}")
                entry_count = len(lines)
                fs_status.update(f"{self.fs_image} - {self.fs_path} - {entry_count} entries ({layer_desc})")
                
        except httpx.RequestError as e:
            fs_status.update(f"Request error: {e}")
        except httpx.HTTPStatusError as e:
            fs_status.update(f"HTTP error: {e.response.status_code}")
    
    def _parse_fslog_line(self, line: str) -> dict | None:
        """Parse a single fslog line into entry dict.
        
        Expected format (from fs-log-sqlite.py):
        drwxr-xr-x       0.0 B  2024-04-22 06:08  bin/
        lrwxrwxrwx       0.0 B  2024-04-22 06:08  bin -> usr/bin
        drwxr-xr-x       0.0 B  2025-10-08 22:11  etc/   [L15] (overridden)
        """
        line = line.strip()
        if not line:
            return None
        
        # Pattern for merged view with layer info: [L15] (overridden)
        # Format: mode  size  date time  name  [layer_info] (overridden)?
        merged_pattern = r'^([drwxlst-]{10})\s+([\d.]+\s+[BKMG]B?)\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s+(.+?)\s+\[L(\d+)\](?:\s+\(overridden\))?$'
        merged_match = re.match(merged_pattern, line)
        
        if merged_match:
            mode, size, date_time, name, layer = merged_match.groups()
            return {
                "mode": mode,
                "size": size.strip(),
                "date": date_time,
                "name": name.strip(),
                "layer": f"L{layer}"
            }
        
        # Pattern for single layer view (no layer info)
        # Format: mode  size  date time  name
        single_pattern = r'^([drwxlst-]{10})\s+([\d.]+\s+[BKMG]B?)\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s+(.+)$'
        single_match = re.match(single_pattern, line)
        
        if single_match:
            mode, size, date_time, name = single_match.groups()
            return {
                "mode": mode,
                "size": size.strip(),
                "date": date_time,
                "name": name.strip(),
                "layer": ""
            }
        
        # Fallback: try to extract what we can
        return None


if __name__ == "__main__":
    app = DockerDorkerApp()
    app.run()
