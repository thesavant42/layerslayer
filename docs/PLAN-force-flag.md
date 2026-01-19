# Implementation Plan: Add `--force` Flag for Unattended Execution

## Overview

Add a `--force` / `-F` flag to enable fully unattended execution by automatically overwriting existing SQLite database entries without prompting.

**Effort:** XS (Extra Small) — ~15 lines changed across 2 files

---

## Files to Modify

| File | Changes |
|------|---------|
| `main.py` | Add `--force` argument, pass to `save_layer_result` calls |
| `app/modules/keepers/storage.py` | Add `force` param to `prompt_overwrite` and `save_layer_result` |

---

## Step 1: Add `--force` Argument to `main.py`

**Location:** `parse_args()` function, after the `--arch` argument (around line 82)

**Code to add:**

```python
    p.add_argument(
        "--force", "-F",
        action="store_true",
        help="Force overwrite of existing database entries without prompting",
    )
```

---

## Step 2: Update `prompt_overwrite` in `storage.py`

**Location:** Lines 162-189

**Changes:**
1. Add `force: bool = False` parameter to function signature
2. Add docstring entry for `force` parameter
3. Before the `input()` call, check if `force` is True and return early

**Updated function:**

```python
def prompt_overwrite(digest: str, conn: sqlite3.Connection, force: bool = False) -> bool:
    """
    Prompt user to confirm overwriting existing layer data.
    
    Shows existing data info and asks for confirmation.
    
    Args:
        digest: Layer digest (sha256:...)
        conn: SQLite connection for fetching existing info
        force: If True, automatically overwrite without prompting
        
    Returns:
        True if user wants to overwrite, False to skip
    """
    info = get_layer_info(conn, digest)
    if not info:
        return True  # No existing data, proceed
    
    short_digest = digest[:19] + "..." if len(digest) > 22 else digest
    
    print(f"\n  Layer {short_digest} already exists in database.")
    print(f"    - Scraped: {info.get('scraped_at', 'unknown')}")
    print(f"    - Entries: {info.get('entries_count', 0):,} files")
    print(f"    - Image: {info.get('image_ref', 'unknown')}")
    print()
    
    if force:
        print("  --force enabled: overwriting automatically")
        return True
    
    response = input("  Overwrite existing data? [y/N]: ").strip().lower()
    return response in ('y', 'yes')
```

---

## Step 3: Update `save_layer_result` Signature in `storage.py`

**Location:** Around line 383

**Changes:**
1. Add `force_overwrite: bool = False` parameter
2. Update docstring
3. Pass `force=force_overwrite` to `prompt_overwrite` call

**Updated signature:**

```python
def save_layer_result(
    result: LayerPeekResult,
    image_ref: str,
    layer_index: int,
    layer_size: int = 0,
    conn: Optional[sqlite3.Connection] = None,
    db_path: str = DEFAULT_DB_PATH,
    json_dir: str = DEFAULT_JSON_DIR,
    check_exists: bool = True,
    force_overwrite: bool = False,  # NEW PARAMETER
) -> tuple[bool, str]:
```

**Updated call to `prompt_overwrite` (around line 417):**

```python
            if not prompt_overwrite(result.digest, conn, force=force_overwrite):
```

---

## Step 4: Update Calls in `main.py`

### Call 1: `--peek-all` mode (line 235)

**Before:**
```python
storage.save_layer_result(result, image_ref, idx, layer_size, conn)
```

**After:**
```python
storage.save_layer_result(result, image_ref, idx, layer_size, conn, force_overwrite=args.force)
```

### Call 2: Interactive mode (line 285)

**Before:**
```python
storage.save_layer_result(result, image_ref, idx, layer_size, conn)
```

**After:**
```python
storage.save_layer_result(result, image_ref, idx, layer_size, conn, force_overwrite=args.force)
```

---

## Usage After Implementation

Fully unattended execution:

```powershell
python main.py -t "moby/buildkit:latest" --peek-all --arch 0 --force
```

---

## Testing Checklist

- [ ] `--force` appears in `python main.py --help`
- [ ] Running with `--force` on existing data auto-overwrites without prompt
- [ ] Running without `--force` on existing data still prompts user
- [ ] Running on new data (no existing entries) works with or without `--force`

---

## Completion Criteria

Task 2 in `RESEARCH.md` is complete when:
1. All code changes are applied
2. All tests pass
3. `python main.py -t "moby/buildkit:latest" --peek-all --arch 0 --force` runs without any user prompts
