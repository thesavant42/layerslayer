"""
FS Simulator Widget - Browse filesystem contents of Docker image layers.

Contains:
- Status display
- Path breadcrumb
- Filesystem DataTable
- fslog line parsing utilities
"""

import re
from textual.app import ComposeResult
from textual.widgets import Static, DataTable


class FSSimulator(Static):
    """Filesystem simulator widget for browsing Docker image layers."""
    
    def compose(self) -> ComposeResult:
        yield Static("Select a layer from config to browse filesystem", id="fs-status")
        yield Static("Path: /", id="fs-breadcrumb")
        yield DataTable(id="fs-table", cursor_type="row")
        yield Static("", id="fs-simulator-spacer")
    
    def setup_table(self) -> None:
        """Configure the filesystem table columns. Call from app on_mount."""
        fs_table = self.query_one("#fs-table", DataTable)
        fs_table.zebra_stripes = True
        fs_table.add_column("MODE", width=12)
        fs_table.add_column("SIZE", width=10)
        fs_table.add_column("DATE", width=18)
        fs_table.add_column("NAME", width=60)
        fs_table.add_column("LAYER", width=8)


def parse_fslog_line(line: str) -> dict | None:
    """Parse a single fslog line into entry dict.
    
    Expected format (from fs-log-sqlite.py):
    drwxr-xr-x       0.0 B  2024-04-22 06:08  bin/
    lrwxrwxrwx       0.0 B  2024-04-22 06:08  bin -> usr/bin
    drwxr-xr-x       0.0 B  2025-10-08 22:11  etc/   [L15] (overridden)
    
    Args:
        line: A single line of fslog output
        
    Returns:
        Dict with mode, size, date, name, layer keys or None if parse fails
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
