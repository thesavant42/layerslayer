# Plan: Make layer_index Mandatory in Carve Functions

## Requirement

**layer_index MUST be a required parameter for all carve operations.** The carve functions must fail immediately with a helpful error if layer_index is not provided.

### Why This Is Critical

1. **File versioning** - The same file path can exist in multiple layers with different content. Users MUST be able to specify which layer version they want.

2. **Performance** - Without a required layer_index, the code falls back to scanning ALL layers sequentially, downloading potentially gigabytes of data. This defeats the entire purpose of targeted extraction.

### Example
- File `/home/example/secret` contains `"0"` on layer 0 and `"password"` on layer 42
- User MUST be able to retrieve either version by specifying the exact layer_index

---

## Affected Code Locations

| Function | File | Line | Current Signature |
|----------|------|------|-------------------|
| `carve_file()` | carver.py | 367 | `layer_index: Optional[int] = None` |
| `carve_file_to_bytes()` | carver.py | 554 | `layer_index: Optional[int] = None` |
| `main()` CLI | carver.py | 729 | No --layer-index argument |

### Fallback Logic to Remove

**carve_file() lines 414-424:**
```python
if layer_index is not None:
    if layer_index < 0 or layer_index >= len(layers):
        return CarveResult(...)
    layers_to_search = [(layer_index, layers[layer_index])]
else:
    layers_to_search = list(enumerate(layers))  # <-- REMOVE THIS
```

**carve_file_to_bytes() lines 597-607:**
```python
if layer_index is not None:
    if layer_index < 0 or layer_index >= len(layers):
        return None, CarveResult(...)
    layers_to_search = [(layer_index, layers[layer_index])]
else:
    layers_to_search = list(enumerate(layers))  # <-- REMOVE THIS
```

---

## Implementation Tasks

### Task 1: Update carve_file() Function Signature

**Location:** Line 367-374

**Change From:**
```python
def carve_file(
    image_ref: str,
    target_path: str,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    verbose: bool = True,
    layer_index: Optional[int] = None,
) -> CarveResult:
```

**Change To:**
```python
def carve_file(
    image_ref: str,
    target_path: str,
    layer_index: int,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    verbose: bool = True,
) -> CarveResult:
```

### Task 2: Remove Fallback Logic in carve_file()

**Location:** Lines 414-424

**Change From:**
```python
if layer_index is not None:
    if layer_index < 0 or layer_index >= len(layers):
        return CarveResult(
            found=False,
            target_file=target_path,
            error=f"Layer index {layer_index} out of range (0-{len(layers)-1})",
        )
    layers_to_search = [(layer_index, layers[layer_index])]
else:
    layers_to_search = list(enumerate(layers))
```

**Change To:**
```python
if layer_index < 0 or layer_index >= len(layers):
    return CarveResult(
        found=False,
        target_file=target_path,
        error=f"Layer index {layer_index} out of range. Valid range: 0-{len(layers)-1}. Use /peek to discover layer indices.",
    )
layers_to_search = [(layer_index, layers[layer_index])]
```

### Task 3: Update carve_file_to_bytes() Function Signature

**Location:** Line 554-560

**Change From:**
```python
def carve_file_to_bytes(
    image_ref: str,
    target_path: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    verbose: bool = False,
    layer_index: Optional[int] = None,
) -> tuple[Optional[bytes], CarveResult]:
```

**Change To:**
```python
def carve_file_to_bytes(
    image_ref: str,
    target_path: str,
    layer_index: int,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    verbose: bool = False,
) -> tuple[Optional[bytes], CarveResult]:
```

### Task 4: Remove Fallback Logic in carve_file_to_bytes()

**Location:** Lines 597-607

**Change From:**
```python
if layer_index is not None:
    if layer_index < 0 or layer_index >= len(layers):
        return None, CarveResult(
            found=False,
            target_file=target_path,
            error=f"Layer index {layer_index} out of range (0-{len(layers)-1})",
        )
    layers_to_search = [(layer_index, layers[layer_index])]
else:
    layers_to_search = list(enumerate(layers))
```

**Change To:**
```python
if layer_index < 0 or layer_index >= len(layers):
    return None, CarveResult(
        found=False,
        target_file=target_path,
        error=f"Layer index {layer_index} out of range. Valid range: 0-{len(layers)-1}. Use /peek to discover layer indices.",
    )
layers_to_search = [(layer_index, layers[layer_index])]
```

### Task 5: Update CLI main() to Require --layer-index

**Location:** Lines 729-771

**Add argument after line 758:**
```python
parser.add_argument(
    "--layer-index", "-l",
    type=int,
    required=True,
    help="Layer index to extract from (required). Use peek functionality to discover layer indices."
)
```

**Update carve_file() call at line 774:**
```python
result = carve_file(
    image_ref=args.image,
    target_path=args.filepath,
    layer_index=args.layer_index,
    output_dir=args.output_dir,
    chunk_size=args.chunk_size * 1024,
    verbose=not args.quiet,
)
```

### Task 6: Update Docstrings

Update docstrings for both functions to reflect that layer_index is now required and explain the rationale.

---

## Verification

After implementation, verify:

1. Calling `carve_file()` without layer_index raises TypeError
2. Calling `carve_file_to_bytes()` without layer_index raises TypeError
3. CLI requires --layer-index flag
4. Invalid layer_index returns helpful error with valid range
5. Valid layer_index extracts from the specified layer only

