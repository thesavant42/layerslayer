# Fix Config Display - Replace Static with DataTable

## Problem
Line ~305 in `app/tui/app.py` - `Static.update(formatted_json)` crashes with MarkupError because Textual interprets `[]` brackets as Rich markup.

## Solution
Replace `Static` widget with `DataTable`. Parse the OCI Image Config JSON and populate DataTable rows.

## OCI Image Config Schema
Per the OCI Image Spec, the config JSON contains:
- `history[]` - Array of build step entries
  - `created` - RFC3339 timestamp
  - `created_by` - Build command/instruction
  - `author` - Optional author string
  - `comment` - Optional comment
  - `empty_layer` - Boolean, true if no filesystem change
- `rootfs.diff_ids[]` - Layer digests (sha256) for non-empty layers
- `config` - Container runtime config (Env, Cmd, Entrypoint, etc.)
- `architecture` - CPU architecture (amd64, arm64, etc.)
- `os` - Operating system (linux, windows)

## Implementation Steps

### 1. app/tui/app.py - Modify RightPanel.compose()
Replace `Static` with `DataTable`:
```python
# Remove:
with VerticalScroll(id="config-scroll"):
    yield Static("", id="config-display")

# Add:
yield DataTable(id="config-table", cursor_type="row")
```

### 2. app/tui/app.py - Add columns on mount
DataTable columns for history entries:
- STEP: Index (1-based)
- DATE: Parsed from `created` timestamp
- COMMAND: The `created_by` instruction
- COMMENT: The `comment` field
- LAYER: Index into diff_ids or "empty"

### 3. app/tui/app.py - Modify fetch_tag_config()
Replace JSON dump with DataTable population:
```python
config_table = self.query_one("#config-table", DataTable)
config_table.clear()

# Setup columns if needed
if not config_table.columns:
    config_table.add_column("STEP", width=5)
    config_table.add_column("DATE", width=12)
    config_table.add_column("COMMAND", width=100)
    config_table.add_column("COMMENT", width=30)
    config_table.add_column("LAYER", width=8)

# Parse ALL history entries
history = config.get("history", [])
diff_ids = config.get("rootfs", {}).get("diff_ids", [])
layer_idx = 0

for i, entry in enumerate(history):
    date = entry.get("created", "")[:10]
    command = entry.get("created_by", "")
    comment = entry.get("comment", "")
    is_empty = entry.get("empty_layer", False)
    
    if is_empty:
        layer = "empty"
    else:
        layer = str(layer_idx)
        layer_idx += 1
    
    config_table.add_row(str(i + 1), date, command, comment, layer)

# Store for peek API
self.layer_digests = diff_ids
```

### 4. app/tui/app.py - Add instance variable
```python
layer_digests: list = []
```

### 5. app/tui/styles.tcss - Update styles
Remove `#config-scroll` and `#config-display` styles. Add:
```css
#config-table {
    height: 1fr;
    margin: 1;
}
```

## Files Modified
- `app/tui/app.py`
- `app/tui/styles.tcss`

## Result
- No MarkupError crashes
- ALL history entries displayed (including empty_layer=true)
- ALL build metadata shown (date, command, comment, layer mapping)
- Layer digests stored in `self.layer_digests` for peek API
