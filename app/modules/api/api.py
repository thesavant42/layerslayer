import sys
import re
import importlib.util
from io import StringIO
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import PlainTextResponse

# Import main module
import main

# Import fs-log-sqlite module using importlib (due to hyphen in filename)
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
def fslog(image: str, path: str, layer: int = Query(default=None)):
    """Browse filesystem logs for a Docker image layer."""
    if not IMAGE_PATTERN.match(image):
        raise HTTPException(status_code=400, detail="Invalid image reference format")
    
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    try:
        if layer is not None:
            sys.argv = ["fs-log-sqlite.py", image, str(layer), path, "--single-layer"]
        else:
            sys.argv = ["fs-log-sqlite.py", image, path]
        fs_log_sqlite.main()
    finally:
        sys.stdout = old_stdout
    
    return captured_output.getvalue()


@app.get("/fslog-search", response_class=PlainTextResponse)
def fslog_search(q: str, image: str = Query(default=None), layer: int = Query(default=None)):
    """Search filesystem logs for files matching a pattern."""
    if image and not IMAGE_PATTERN.match(image):
        raise HTTPException(status_code=400, detail="Invalid image reference format")
    
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    try:
        sys.argv = ["fs-log-sqlite.py", "--search", q]
        if image:
            sys.argv.append(image)
            if layer is not None:
                sys.argv.append(str(layer))
        fs_log_sqlite.main()
    finally:
        sys.stdout = old_stdout
    
    return captured_output.getvalue()
