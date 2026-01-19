# layerslayer.py

import os
import sys
import argparse

from app.modules.keepers.downloaders import get_manifest, download_layer_blob, fetch_build_steps
from app.modules.finders.peekers import peek_layer_blob, peek_layer_blob_complete
from app.modules.keepers.layerSlayerResults import layerslayer as layerslayer_bulk, LayerPeekResult


from app.modules.formatters import (
    parse_image_ref,
    registry_base_url,
    human_readable_size,
)

from app.modules.keepers.carver import carve_file, CarveResult

# split output to file and stdout
class Tee:
    """Duplicate stdout/stderr to a file and the console."""
    def __init__(self, *files):
        self.files = files
    def write(self, data):
        for f in self.files:
            f.write(data)
    def flush(self):
        for f in self.files:
            f.flush()

#----- Tar format entry
def format_entry_line(entry, show_permissions=True):
    """
    Format a TarEntry for display, similar to ls -la output.
    
    Args:
        entry: TarEntry object with rich metadata
        show_permissions: Whether to show full ls -la style output
    
    Returns:
        Formatted string for display
    """
    if show_permissions:
        # Full ls -la style: drwxr-xr-x  0  0  2024-01-15 10:30  filename
        size_str = human_readable_size(entry.size).rjust(8)
        if entry.is_symlink and entry.linkname:
            name_display = f"{entry.name} -> {entry.linkname}"
        else:
            name_display = entry.name + ("/" if entry.is_dir else "")
        return f"  {entry.mode}  {entry.uid:4d} {entry.gid:4d}  {size_str}  {entry.mtime}  {name_display}"
    else:
        # Simple format
        if entry.is_dir:
            return f"  [DIR]  {entry.name}/"
        elif entry.is_symlink:
            return f"  [LINK] {entry.name} -> {entry.linkname}"
        else:
            size_str = human_readable_size(entry.size)
            return f"  [FILE] {entry.name} ({size_str})"

# --- layer peek 
def display_peek_result(result: LayerPeekResult, layer_size: int, verbose: bool = False):
    """
    Display the results of a layer peek operation.
    
    Args:
        result: LayerPeekResult from peek functions
        layer_size: Full layer size in bytes (for comparison)
        verbose: Whether to show detailed stats
    """
    if result.error:
        print(f"  [!] Error: {result.error}")
        return
    
    # Show efficiency stats
    if verbose or result.bytes_downloaded > 0:
        pct = (result.bytes_downloaded / layer_size * 100) if layer_size > 0 else 0
        print(f"\n  [Stats] Downloaded: {human_readable_size(result.bytes_downloaded)} "
              f"of {human_readable_size(layer_size)} ({pct:.2f}%)")
        if result.partial:
            print(f"  [Stats] Files found: {result.entries_found} (partial)")
        else:
            print(f"  [Stats] Files found: {result.entries_found} (complete)")
    
    print("\n  Layer contents:\n")
    
    for entry in result.entries:
        print(format_entry_line(entry, show_permissions=True))

