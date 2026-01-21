import sys
import re
import importlib.util
from io import StringIO
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
import httpx
import requests

# Import main module
import main

# Import image config fetcher
from app.modules.finders import get_image_config

# Import fs-log-sqlite module using importlib (due to hyphen in filename)
spec = importlib.util.spec_from_file_location("fs_log_sqlite", "app/modules/fs-log-sqlite.py")
fs_log_sqlite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs_log_sqlite)

app = FastAPI(title="LSNG Peek API")

# Validate image reference format to prevent injection
IMAGE_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*/[a-zA-Z0-9][a-zA-Z0-9._-]*(:[a-zA-Z0-9._-]+)?$')


@app.get("/peek", response_class=PlainTextResponse)
def peek(
    image: str,
    layer: str = Query(default="all"),
    arch: int = Query(default=0),
    hide_build: bool = Query(default=False, description="Hide build steps output")
):
    """
    Equivalent to: python main.py -t "{image}" --peek-layer={layer} --arch={arch} --force
    
    Args:
        image: Image reference (e.g., "nginx/nginx:latest")
        layer: Layer to peek - 'all' for all layers, or integer index for specific layer
        arch: Platform index for multi-arch images
        hide_build: If true, hide verbose build steps output
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
            f"--peek-layer={layer}",
            f"--arch={arch}",
            "--force"
        ]
        if hide_build:
            sys.argv.append("--hide-build")
        
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


@app.get("/repositories")
async def repositories(
    namespace: str,
    page: int = Query(default=None),
    page_size: int = Query(default=None)
):
    """
    Pass-through proxy for Docker Hub's /v2/repositories API.
    Returns the upstream JSON response verbatim.
    """
    url = f"https://hub.docker.com/v2/repositories/{namespace}"
    params = {}
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["page_size"] = page_size
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return JSONResponse(content=response.json(), status_code=200)


@app.get("/repositories/{namespace}/{repo}/tags")
async def repository_tags(
    namespace: str,
    repo: str,
    page: int = Query(default=None),
    page_size: int = Query(default=None),
    ordering: str = Query(default="last_updated")
):
    """
    Pass-through proxy for Docker Hub's repository tags API.
    Returns the upstream JSON response verbatim.
    """
    url = f"https://hub.docker.com/v2/repositories/{namespace}/{repo}/tags"
    params = {"ordering": ordering}
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["page_size"] = page_size
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return JSONResponse(content=response.json(), status_code=200)


@app.get("/repositories/{namespace}/{repo}/tags/{tag}/images")
async def repository_tag_images(
    namespace: str,
    repo: str,
    tag: str,
    page: int = Query(default=None),
    page_size: int = Query(default=None),
    ordering: str = Query(default="last_updated")
):
    """
    Pass-through proxy for Docker Hub's repository tag images API.
    Returns the upstream JSON response verbatim.
    """
    url = f"https://hub.docker.com/v2/repositories/{namespace}/{repo}/tags/{tag}/images"
    params = {"ordering": ordering}
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["page_size"] = page_size
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return JSONResponse(content=response.json(), status_code=200)


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


@app.get("/repositories/{namespace}/{repo}/tags/{tag}/config")
def get_tag_config(
    namespace: str,
    repo: str,
    tag: str,
    arch: str = Query(default=None, description="Target architecture: amd64, arm64, etc.")
):
    """
    Fetch the full image configuration JSON for a tagged image.
    
    Returns environment variables, entrypoint, cmd, working directory,
    labels, build history, and other image metadata.
    """
    try:
        config = get_image_config(
            namespace=namespace,
            repo=repo,
            tag=tag,
            arch=arch
        )
        return JSONResponse(content=config, status_code=200)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Registry request failed: {e}")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
