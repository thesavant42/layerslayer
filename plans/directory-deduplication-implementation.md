# Directory Deduplication Implementation Plan

## Overview
Fix duplicate directory entries in the FS Simulator merged view by keeping only the highest layer number for each directory.

## Scope
**This is a display-only change.** No database modifications are made. The fix filters data in the TUI presentation layer before rendering to the DataTable widget. The fslog API response and SQLite database remain completely unchanged.

## Problem Statement
When viewing the merged/combined view in the FS Simulator, directories that exist in multiple layers are shown multiple times. For example, `etc/` appears 14 times because it exists in 14 different layers.

## Root Cause
The [`_do_load_fslog()`](app/tui/app.py:633) method iterates through all lines returned by the fslog API and adds every entry directly to the DataTable without deduplication.

## Solution

### File to Modify
- **File:** `app/tui/app.py`
- **Method:** `_do_load_fslog()` (lines 633-677)

### Implementation Details

#### Current Code (lines 654-668)
```python
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
```

#### New Code (replace lines 654-668)
```python
fs_table.clear()

if self.fs_path != "/":
    fs_table.add_row("", "", "", "..", "")

# Parse all entries
entries = []
for line in lines:
    entry = parse_fslog_line(line)
    if entry:
        entries.append(entry)

# Deduplicate directories: keep only highest layer number for each directory
# Files are kept as-is since different layers may have different versions
if self.fs_layer is None:  # Only deduplicate in merged view
    dir_entries = {}  # name -> entry with highest layer
    file_entries = []
    
    for entry in entries:
        name = entry["name"]
        layer_str = entry.get("layer", "")
        
        if name.endswith("/"):  # Directory
            # Extract layer number from "L15" format
            layer_num = int(layer_str[1:]) if layer_str.startswith("L") else -1
            
            if name not in dir_entries:
                dir_entries[name] = (entry, layer_num)
            else:
                # Keep the entry with higher layer number
                existing_layer = dir_entries[name][1]
                if layer_num > existing_layer:
                    dir_entries[name] = (entry, layer_num)
        else:  # File
            file_entries.append(entry)
    
    # Combine: directories first, then files
    entries = [e for e, _ in dir_entries.values()] + file_entries

# Add rows to table
for entry in entries:
    fs_table.add_row(
        entry["mode"],
        entry["size"],
        entry["date"],
        entry["name"],
        entry.get("layer", "")
    )
```

### Key Design Decisions

1. **Only deduplicate in merged view**: The condition `if self.fs_layer is None` ensures deduplication only happens in the merged/combined view, not when viewing a specific layer.

2. **Keep highest layer number**: For directories, we keep the entry with the highest layer number since that represents the most recent version in the overlay filesystem.

3. **Preserve file entries**: Files are not deduplicated because different layers may have different versions of the same file that users want to compare.

4. **Maintain directory-first ordering**: Directories are listed before files, which is the standard convention.

### Testing

After implementation, verify:
1. In merged view of `/`, directories like `bin/`, `etc/`, `usr/` should appear only once
2. Each directory should show the highest layer number (e.g., `L19` not `L0`)
3. When viewing a specific layer, all entries should still appear as before
4. Files should still show all entries across layers if they exist in multiple layers

## Todo List for Coding Agent

```
[ ] Open app/tui/app.py
[ ] Navigate to the _do_load_fslog() method (line 633)
[ ] Replace lines 654-668 with the new deduplication logic
[ ] Save the file
[ ] Test by running the TUI and browsing the merged view of an image
```
