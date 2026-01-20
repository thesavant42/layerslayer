# FastAPI /peek-all Endpoint Implementation Plan
**COMPLETED This has been implemented.**
## Approach

Set `sys.argv` with the query parameters, then call `main.main()` directly. This mirrors exactly what happens when you run the CLI command - no subprocess, no code refactoring needed.

---

## Endpoint

```
GET /peek-all?image={image}&arch={arch}
```

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `image` | Yes | - | Container reference `owner/repo:tag` |
| `arch` | No | `0` | Architecture index |

`--force` is always applied.

---

## File Location

```
app/modules/api/
    __init__.py
    api.py
```

---

## Code

### app/modules/api/api.py

```python
import sys
import re
from io import StringIO
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import PlainTextResponse

# Import main module
import main

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
```

### app/modules/api/__init__.py

```python
from .api import app
```

---

## How It Works

1. Browser hits: `http://localhost:8000/peek-all?image=moby/buildkit:latest&arch=0`
2. FastAPI validates `image` against regex pattern (prevents malformed input)
3. Sets `sys.argv` to simulate CLI invocation
4. Calls `main.main()` which:
   - Parses args via `parse_args()`
   - Executes `--peek-all` branch (lines 218-243)
5. Captures stdout and returns it as plain text

---

## Input Validation

The regex `^[a-zA-Z0-9][a-zA-Z0-9._-]*/[a-zA-Z0-9][a-zA-Z0-9._-]*(:[a-zA-Z0-9._-]+)?$` validates:
- Namespace: starts with alphanumeric, allows `.` `_` `-`
- `/` separator
- Repository: starts with alphanumeric, allows `.` `_` `-`
- Optional `:tag`

Rejects anything that does not match this pattern.

---

## Dependencies

Add to `requirements.txt`:
```
fastapi
uvicorn
```

---

## How to Run

```bash
uvicorn app.modules.api.api:app --host 0.0.0.0 --port 8000
```

---

## Implementation Checklist COMPLETED!

- [x] Create `app/modules/api/__init__.py`
- [x] Create `app/modules/api/api.py`
- [x] Add `fastapi` and `uvicorn` to `requirements.txt`
- [x] Test endpoint
- [x] Update `docs/RESEARCH.md` Task 3 as complete
