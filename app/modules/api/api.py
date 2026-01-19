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
