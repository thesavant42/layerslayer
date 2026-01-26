# Fix Plan: update_layer_peeked() Function Signature Mismatch

## Problem Summary

The `/peek` endpoint crashes with:
```
TypeError: update_layer_peeked() takes from 3 to 4 positional arguments but 6 were given
```

## Current Code

### app/modules/api/api.py - Lines 539, 544

The API calls `update_layer_peeked()` with 6 arguments:

```python
# Line 539
update_layer_peeked(conn, namespace, repo, tag, arch_str, idx)

# Line 544
update_layer_peeked(conn, namespace, repo, tag, arch_str, layer_idx)
```

### app/modules/keepers/storage.py - Lines 752-776

The function only accepts 3-4 arguments:

```python
# Lines 752-776
def update_layer_peeked(
    conn: sqlite3.Connection,
    config_digest: str,
    layer_index: int,
    entries_count: int = 0,
) -> None:
    """
    Mark a layer as peeked.
    
    Args:
        conn: SQLite connection
        config_digest: Config digest the layer belongs to
        layer_index: Layer index to mark as peeked
        entries_count: Number of filesystem entries found
    """
    cursor = conn.cursor()
    peeked_at = datetime.now().isoformat()
    
    cursor.execute("""
        UPDATE image_layers
        SET peeked = 1, peeked_at = ?, entries_count = ?
        WHERE config_digest = ? AND layer_index = ?
    """, (peeked_at, entries_count, config_digest, layer_index))
    
    conn.commit()
```

## Fix: Replace Lines 752-776 in storage.py

Replace the entire `update_layer_peeked()` function with:

```python
def update_layer_peeked(
    conn: sqlite3.Connection,
    owner: str,
    repo: str,
    tag: str,
    arch: str,
    layer_index: int,
    entries_count: int = 0,
) -> bool:
    """
    Mark a layer as peeked.
    
    Looks up config_digest from image_configs table using owner/repo/tag/arch,
    then updates the corresponding layer in image_layers.
    
    Args:
        conn: SQLite connection
        owner: Image namespace/owner
        repo: Repository name
        tag: Image tag
        arch: Architecture (e.g., "amd64")
        layer_index: Layer index to mark as peeked
        entries_count: Number of filesystem entries found
        
    Returns:
        True if layer was marked as peeked, False if config not found
    """
    cursor = conn.cursor()
    
    # Look up config_digest from image identifiers
    cursor.execute("""
        SELECT config_digest
        FROM image_configs
        WHERE owner = ? AND repo = ? AND tag = ? AND arch = ?
    """, (owner, repo, tag, arch))
    
    row = cursor.fetchone()
    if not row:
        return False  # Config not cached, cannot update
    
    config_digest = row["config_digest"]
    peeked_at = datetime.now().isoformat()
    
    cursor.execute("""
        UPDATE image_layers
        SET peeked = 1, peeked_at = ?, entries_count = ?
        WHERE config_digest = ? AND layer_index = ?
    """, (peeked_at, entries_count, config_digest, layer_index))
    
    conn.commit()
    return True
```

## Verification

After the fix, the call sites in api.py (lines 539, 544) will match:

| Parameter | api.py passes | storage.py expects |
|-----------|--------------|-------------------|
| 1 | conn | conn |
| 2 | namespace | owner |
| 3 | repo | repo |
| 4 | tag | tag |
| 5 | arch_str | arch |
| 6 | idx/layer_idx | layer_index |

## Files to Modify

- `app/modules/keepers/storage.py` - Replace lines 752-776

## No Changes Needed

- `app/modules/api/api.py` - Call sites already correct
