# FastAPI /fslog and /fslog-search Endpoint Implementation Plan

## Approach

Same minimalist technique as [`/peek-all`](../docs/api/fastapi-peek-all.md):
- Import the Python script ([`fs-log-sqlite.py`](../app/modules/fs-log-sqlite.py))
- Set `sys.argv` with query parameters
- Call `main()` directly  
- Capture stdout and return as plain text

---

## Task 1: /fslog Route

### Endpoint
```
GET /fslog?image={image_ref}&path={path}&layer={layer}&help={help}
```

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `image` | Yes | - | Image reference `owner/repo:tag` |
| `path` | Yes | - | Directory path to list (e.g., `/` or `/etc`) |
| `layer` | No | - | Layer index; when provided, shows single layer view |
| `help` | No | `false` | When `true`, return help message |

### Behavior Mapping to CLI

| API Call | Equivalent CLI |
|----------|----------------|
| `/fslog?image=alpine/git:v2.52.0&path=/` | `fs-log-sqlite.py alpine/git:v2.52.0 "/"` |
| `/fslog?image=alpine/git:v2.52.0&path=/etc` | `fs-log-sqlite.py alpine/git:v2.52.0 "/etc"` |
| `/fslog?image=alpine/git:v2.52.0&path=/&layer=0` | `fs-log-sqlite.py alpine/git:v2.52.0 0 "/" --single-layer` |
| `/fslog?help=true` | `fs-log-sqlite.py --help` |

### Implementation Notes

- When `layer` parameter is provided, automatically add `--single-layer` flag
- When `help=true`, return the argparse help output
- Validate `image` format using existing `IMAGE_PATTERN` regex
- Validate `path` starts with `/`

---

## Task 2: /fslog-search Route

### Endpoint
```
GET /fslog-search?q={pattern}&image={image_ref}&layer={layer}
```

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `q` | Yes | - | Search pattern (supports SQL LIKE patterns) |
| `image` | No | - | Filter results to specific image |
| `layer` | No | - | Filter results to specific layer index |

### Behavior Mapping to CLI

| API Call | Equivalent CLI |
|----------|----------------|
| `/fslog-search?q=shadow` | `fs-log-sqlite.py --search shadow` |
| `/fslog-search?q=shadow&image=alpine/git:v2.52.0` | `fs-log-sqlite.py --search shadow alpine/git:v2.52.0` |
| `/fslog-search?q=shadow&image=alpine/git:v2.52.0&layer=0` | `fs-log-sqlite.py --search shadow alpine/git:v2.52.0 0` |

### Implementation Notes

- `q` is required - return 400 error if missing
- `image` and `layer` are optional filters
- Validate `image` format if provided
- Validate `layer` is integer if provided

---

## Code Location

Extend existing file:
```
app/modules/api/api.py
```

---

## Implementation Checklist

- [ ] Add import for `fs-log-sqlite` module in [`api.py`](../app/modules/api/api.py)
- [ ] Add `/fslog` route with parameters: `image`, `path`, `layer`, `help`
- [ ] Add `/fslog-search` route with parameters: `q`, `image`, `layer`
- [ ] Add input validation for `path` parameter (must start with `/`)
- [ ] Test `/fslog` endpoint with merged view (no layer param)
- [ ] Test `/fslog` endpoint with single layer view (layer param)
- [ ] Test `/fslog` endpoint help output
- [ ] Test `/fslog-search` endpoint with pattern only
- [ ] Test `/fslog-search` endpoint with image filter
- [ ] Test `/fslog-search` endpoint with image and layer filter
- [ ] Update task documentation as complete

---

## Complete Implementation Code

This is the complete code that will be added to [`api.py`](../app/modules/api/api.py):

```python
import sys
import re
from io import StringIO
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import PlainTextResponse

# Import main module
import main

# Import fs-log-sqlite module using importlib (due to hyphen in filename)
import importlib.util
spec = importlib.util.spec_from_file_location("fs_log_sqlite", "app/modules/fs-log-sqlite.py")
fs_log_sqlite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs_log_sqlite)

app = FastAPI(title="LSNG Peek API")

# Validate image reference format to prevent injection
IMAGE_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*/[a-zA-Z0-9][a-zA-Z0-9._-]*(:[a-zA-Z0-9._-]+)?$')


@app.get("/peek-all", response_class=PlainTextResponse)
def peek_all(
    image: str,
    arch: int = Query(default=0)
):
    """
    Execute --peek-all for the specified image.
    Equivalent to: python main.py -t "{image}" --peek-all --arch={arch} --force
    """
    # Validate image format
    if not IMAGE_PATTERN.match(image):
        raise HTTPException(status_code=400, detail="Invalid image reference format")
    
    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    try:
        # Set argv as if called from CLI
        sys.argv = [
            "main.py",
            "-t", image,
            "--peek-all",
            f"--arch={arch}",
            "--force"
        ]
        
        # Call main directly
        main.main()
        
    finally:
        # Restore stdout
        sys.stdout = old_stdout
    
    return captured_output.getvalue()


@app.get("/fslog", response_class=PlainTextResponse)
def fslog(
    image: str = Query(default=None),
    path: str = Query(default=None),
    layer: int = Query(default=None),
    help: bool = Query(default=False, alias="help")
):
    """
    Browse filesystem logs for a Docker image layer.
    
    - Without layer: shows merged view of all layers
    - With layer: shows single layer view (--single-layer mode)
    - With help=true: returns help message
    """
    # Handle help request
    if help:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = captured_output = StringIO()
        sys.stderr = captured_output
        
        try:
            sys.argv = ["fs-log-sqlite.py", "--help"]
            try:
                fs_log_sqlite.main()
            except SystemExit:
                pass  # argparse calls sys.exit after --help
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        
        return captured_output.getvalue()
    
    # Validate required parameters
    if not image or not path:
        raise HTTPException(
            status_code=400,
            detail="Missing required parameters: image and path are required. Use help=true for usage info."
        )
    
    # Validate image format
    if not IMAGE_PATTERN.match(image):
        raise HTTPException(status_code=400, detail="Invalid image reference format")
    
    # Validate path starts with /
    if not path.startswith("/"):
        raise HTTPException(status_code=400, detail="Path must start with /")
    
    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    try:
        # Build argv based on parameters
        if layer is not None:
            # Single layer mode: image layer path --single-layer
            sys.argv = [
                "fs-log-sqlite.py",
                image,
                str(layer),
                path,
                "--single-layer"
            ]
        else:
            # Merged mode: image path
            sys.argv = [
                "fs-log-sqlite.py",
                image,
                path
            ]
        
        fs_log_sqlite.main()
        
    finally:
        sys.stdout = old_stdout
    
    return captured_output.getvalue()


@app.get("/fslog-search", response_class=PlainTextResponse)
def fslog_search(
    q: str,
    image: str = Query(default=None),
    layer: int = Query(default=None)
):
    """
    Search filesystem logs for files matching a pattern.
    
    - q: Search pattern (supports SQL LIKE patterns)
    - image: Optional filter to specific image
    - layer: Optional filter to specific layer index
    """
    # Validate image format if provided
    if image and not IMAGE_PATTERN.match(image):
        raise HTTPException(status_code=400, detail="Invalid image reference format")
    
    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    try:
        # Build argv: --search pattern [image] [layer]
        sys.argv = ["fs-log-sqlite.py", "--search", q]
        
        if image:
            sys.argv.append(image)
            if layer is not None:
                sys.argv.append(str(layer))
        
        fs_log_sqlite.main()
        
    finally:
        sys.stdout = old_stdout
    
    return captured_output.getvalue()
```

---

## Summary of Changes to api.py

1. **Add import** for `fs-log-sqlite` module using `importlib` (required due to hyphen in filename)
2. **Add `/fslog` endpoint** - filesystem browser with merged/single-layer views
3. **Add `/fslog-search` endpoint** - file/directory search functionality
